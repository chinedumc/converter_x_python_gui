from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse, FileResponse
from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional
import uvicorn
import jwt
import os
from dotenv import load_dotenv
from ratelimit import limits, RateLimitException
import logging
from logging.handlers import TimedRotatingFileHandler
import re
import json
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
from config import Config

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Excel to XML Converter API",
    description="A secure API for converting Excel files to XML format",
    version="1.0.0"
)

# Create an APIRouter with the /api/v1 prefix
api_router = APIRouter(prefix="/api/v1")

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5  # 5 minutes session timeout

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost","http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SizeAndTimeRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='midnight', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None, maxBytes=20*1024*1024):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.maxBytes = maxBytes

    def shouldRollover(self, record):
        # Time-based rollover
        if super().shouldRollover(record):
            return 1
        # Size-based rollover
        if self.stream is None:  # Delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:
            self.stream.seek(0, 2)  # Go to end of file
            if self.stream.tell() + len(self.format(record).encode(self.encoding or "utf-8")) >= self.maxBytes:
                return 1
        return 0

# Set up log directory and file
log_file = Config.LOG_FILE_PATH
log_dir = os.path.dirname(log_file)
os.makedirs(log_dir, exist_ok=True)

# Remove any previous handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

handler = SizeAndTimeRotatingFileHandler(
    log_file,
    when='midnight',
    backupCount=30,  # Keep up to 30 log files
    encoding='utf-8',
    maxBytes=20*1024*1024  # 20MB
)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    force=True
)
log = logging.getLogger("converter_x")
log.info("Test log entry: Backend started")

# Rate limiting decorator - 100 requests per minute
@limits(calls=100, period=60)
def check_rate_limit():
    pass

# Middleware for session timeout
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    try:
        # Check rate limit
        check_rate_limit()
        
        # Get token from header
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                exp = payload.get("exp")
                if not exp or datetime.utcfromtimestamp(exp) < datetime.utcnow():
                    raise HTTPException(status_code=401, detail="Session expired")
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="Invalid token")
    except RateLimitException:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    
    response = await call_next(request)
    return response

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# File conversion endpoint
@api_router.post("/convert")
async def convert_excel_to_xml(
    file: UploadFile = File(...),
    header_fields: str = Form(None)
):
    try:
        log.info(f"File upload attempt: {file.filename}")
        log.info(f"Raw header_fields received: {header_fields}")

        header_fields_dict = {}
        if header_fields:
            header_fields_dict = json.loads(header_fields)
        if isinstance(header_fields_dict, list):
            header_fields_dict = {
                item["tagName"]: item["tagValue"]
                for item in header_fields_dict
                if "tagName" in item and "tagValue" in item
            }
        log.info(f"Parsed header_fields_dict: {header_fields_dict}")

        # Read the uploaded file directly into memory
        file_content = await file.read()

        # Process the file content (e.g., read it into a DataFrame)
        df = pd.read_excel(file_content)
        sanitized_columns = [sanitize_tag(col) for col in df.columns]
        log.info(f"Sanitized XML tags: {sanitized_columns}")

        # Create XML root
        root = ET.Element("CALLREPORT")
        # Add header fields
        header = ET.SubElement(root, "HEADER")
        for k, v in header_fields_dict.items():
            tag = sanitize_tag(k)
            ET.SubElement(header, tag).text = str(v)
        # Add data rows
        body_section = ET.SubElement(root, "BODY")
        for _, row in df.iterrows():
            record = ET.SubElement(body_section, "CALLREPORT_DATA")
            for col in df.columns:
                tag = sanitize_tag(col)
                ET.SubElement(record, tag).text = str(row[col])

        # Convert to string
        rough_string = ET.tostring(root, encoding="utf-8", method="xml")
        reparsed = minidom.parseString(rough_string)
        xml_content = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        if xml_content.startswith(b'\n'):
            xml_content = xml_content.lstrip(b'\n')

        # Generate a unique filename using date-time-second
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"converted_{timestamp}.xml"
        output_path = os.path.join(Config.OUTPUT_DIR, saved_filename)

        # Save XML content to file
        with open(output_path, "wb") as f:
            f.write(xml_content)
        log.info(f"File conversion successful: {file.filename} -> {saved_filename}")

        download_url = f"/api/v1/download/{saved_filename}"
        log.info(f"Download URL generated: {download_url}")
        return {
            "status": "success",
            "message": "Conversion completed",
            "downloadUrl": download_url
        }
    except Exception as e:
        import traceback
        log.error(f"Conversion failed for file: {file.filename} - {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An error occurred during the conversion process. Please try again later.")

@api_router.get("/download/{filename}")
async def download_file(filename: str):
    output_dir = Config.OUTPUT_DIR
    file_path = os.path.join(output_dir, filename)
    log.info(f"Download attempt for file: {filename}")
    if not os.path.exists(file_path):
        log.error(f"File not found for download: {filename}")
        raise HTTPException(status_code=404, detail="File not found")
    log.info(f"File download successful: {filename}")
    return FileResponse(file_path, filename=filename)

# Register the router with the app
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

def sanitize_tag(tag):
    # Replace spaces with underscores
    tag = re.sub(r'\s+', '_', tag)
    # Remove invalid characters (allow only letters, digits, underscore, hyphen, period)
    tag = re.sub(r'[^a-zA-Z0-9_.-]', '', tag)
    # Ensure tag starts with a letter or underscore
    if not re.match(r'^[a-zA-Z_]', tag):
        tag = '_' + tag
    # If tag is empty after sanitization, use a fallback
    if not tag:
        tag = 'EMPTY_TAG'
    return tag

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)