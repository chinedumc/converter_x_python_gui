from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import json
from datetime import datetime
import uuid
from pathlib import Path
import logging
import re
import os

# If you want to use rate limiting, ensure the correct library is installed and imported.
# Otherwise, remove the decorator and related import.
# from slowapi.util import limits  # Uncomment if slowapi is installed and available

from ..models.schemas import (
    ConversionRequest,
    ConversionResponse,
    FileValidationResponse,
    HealthResponse
)
from ..utils.converter import converter
from ..utils.audit import audit_logger
from ..utils.encryption import encryption
from ..config import config

logger = logging.getLogger("converter_x")

router = APIRouter(prefix=config.API_V1_PREFIX)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=config.XML_SCHEMA_VERSION,
        timestamp=datetime.utcnow()
    )

@router.post("/validate", response_model=FileValidationResponse)
async def validate_file(
    file: UploadFile = File(...)
):
    """Validate Excel file before conversion."""
    logger.info(f"File upload attempt: filename={file.filename}, content_type={file.content_type}")
    try:
        # Get file size and type
        file_size = 0
        chunk_size = 8192
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
        await file.seek(0)

        # Validate file size
        if file_size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return FileValidationResponse(
                is_valid=False,
                message=f"File size exceeds {config.MAX_UPLOAD_SIZE_MB}MB limit",
                file_size=file_size,
                file_type=Path(file.filename).suffix
            )

        # Validate file type
        if not config.validate_file_extension(file.filename):
            return FileValidationResponse(
                is_valid=False,
                message="Invalid file type. Only .xls and .xlsx files are allowed",
                file_size=file_size,
                file_type=Path(file.filename).suffix
            )

        # Save file temporarily for validation
        temp_path = config.UPLOAD_DIR / f"temp_{uuid.uuid4()}{Path(file.filename).suffix}"
        with open(temp_path, "wb") as temp_file:
            await file.seek(0)
            content = await file.read()
            temp_file.write(content)

        # Validate Excel content
        is_valid = converter.validate_excel_file(temp_path)

        # Clean up temporary file
        temp_path.unlink()

        logger.info(f"File upload success: filename={file.filename}")
        return FileValidationResponse(
            is_valid=is_valid,
            message="File is valid" if is_valid else "Invalid Excel file format",
            file_size=file_size,
            file_type=Path(file.filename).suffix
        )

    except Exception as e:
        logger.error(f"File upload failed: filename={file.filename}, error={str(e)}")
        audit_logger.log_error(
            user_id="system",
            action="validate_file",
            error=e,
            details={"filename": file.filename}
        )
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/convert", response_model=ConversionResponse)
async def convert_file(
    file: UploadFile = File(...),
    request_data: Optional[str] = Form(None)
):
    """Convert Excel file to XML with optional header fields."""
    start_time = datetime.now()
    file_size = 0
    try:
        # Get file size
        chunk_size = 8192
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
        await file.seek(0)

        # Log file upload attempt
        audit_logger.log_file_operation(
            user_id="system",
            action="upload",
            file_name=file.filename,
            file_size=file_size,
            file_type=Path(file.filename).suffix
        )

        # Parse request data
        header_fields = {}
        if request_data:
            try:
                request_dict = json.loads(request_data)
                # Get header fields as array of objects
                header_array = request_dict.get('header_fields', [])
                # Convert to dictionary format expected by converter
                for field in header_array:
                    if 'tagName' in field and 'tagValue' in field:
                        # Preserve exact case of tag name as entered by user
                        tag_name = field['tagName']
                        # Replace spaces with underscores
                        tag_name = tag_name.replace(' ', '_')
                        header_fields[tag_name] = field['tagValue']
            except json.JSONDecodeError as e:
                audit_logger.log_conversion_event(
                    user_id="system",
                    input_file=file.filename,
                    output_file="",
                    conversion_time=0.0,
                    status="error",
                    details={"error": f"Invalid request data format: {str(e)}"}
                )
                raise HTTPException(status_code=400, detail="Invalid request data format")
            except Exception as e:
                audit_logger.log_conversion_event(
                    user_id="system",
                    input_file=file.filename,
                    output_file="",
                    conversion_time=0.0,
                    status="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=400, detail=str(e))

        # Generate unique file names
        file_id = str(uuid.uuid4())
        input_path = config.UPLOAD_DIR / f"{file_id}_input{Path(file.filename).suffix}"
        output_path = config.OUTPUT_DIR / f"{file_id}_output.xml"

        # Save uploaded file using streaming
        try:
            total_size = 0
            with open(input_path, "wb") as f:
                async for chunk in file.stream():
                    total_size += len(chunk)
                    f.write(chunk)
                    
                    # Check file size limit during streaming
                    if total_size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                        f.close()
                        input_path.unlink()
                        raise HTTPException(
                            status_code=413,
                            detail=f"File size exceeds {config.MAX_UPLOAD_SIZE_MB}MB limit"
                        )
            
            audit_logger.log_file_operation(
                user_id="system",
                action="save",
                file_name=str(input_path),
                file_size=total_size,
                file_type=Path(file.filename).suffix
            )
        except Exception as e:
            if input_path.exists():
                input_path.unlink()
            audit_logger.log_error(
                user_id="system",
                action="save",
                error=e,
                details={"file_name": str(input_path)}
            )
            raise

        # Convert file
        # Set encrypt_output to False or retrieve from request_dict if needed
        encrypt_output = request_dict.get('encrypt_output', False) if 'request_dict' in locals() else False
        converter.convert(
            input_file=input_path,
            output_file=output_path,
            header_fields=header_fields,
            sheet_name=request_dict.get('sheet_name') if 'request_dict' in locals() else None,
            encrypt_output=encrypt_output
        )

        # Generate download URL
        download_url = f"{config.API_V1_PREFIX}/download/{file_id}"

        # Log successful conversion
        conversion_time = (datetime.now() - start_time).total_seconds()
        audit_logger.log_conversion_event(
            user_id="system",
            input_file=file.filename,
            output_file=str(output_path),
            conversion_time=conversion_time,
            status="success",
            details={
                "input_size": file_size,
                "output_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
                "header_fields": len(header_fields or {})
            }
        )

        return ConversionResponse(
            status="success",
            message="File converted successfully",
            downloadUrl=download_url
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Cleanup input and output files
        for cleanup_path in [input_path, output_path]:
            if cleanup_path.exists():
                cleanup_path.unlink()
                audit_logger.log_file_operation(
                    user_id="system",
                    action="delete",
                    file_name=str(cleanup_path),
                    file_size=0,
                    file_type=cleanup_path.suffix
                )

@router.get("/download/{file_id}")
# @limits(calls=30, period=60)  # Uncomment if using slowapi for rate limiting
async def download_file(file_id: str):
    try:
        # Check for both encrypted and unencrypted files
        encrypted_path = config.OUTPUT_DIR / f"{file_id}.xml.enc"
        unencrypted_path = config.OUTPUT_DIR / f"{file_id}.xml"
        
        if not encrypted_path.exists() and not unencrypted_path.exists():
            audit_logger.log_file_operation(
                user_id="system",
                action="download",
                file_name=f"{file_id}.xml",
                file_size=0,
                file_type=".xml",
                status="error",
                details={"error": "File not found"}
            )
            raise HTTPException(status_code=404, detail="File not found")

        # Create temporary file for decrypted content if needed
        temp_path = config.OUTPUT_DIR / f"temp_{file_id}.xml"
        
        # Use unencrypted file if it exists, otherwise decrypt the encrypted file
        if unencrypted_path.exists():
            temp_path = unencrypted_path
        else:
            # Log download attempt
            audit_logger.log_file_operation(
                user_id="system",
                action="download",
                file_name=str(encrypted_path),
                file_size=os.path.getsize(encrypted_path),
                file_type=".xml"
            )
            
            # Decrypt file
            encryption.decrypt_file(encrypted_path, temp_path)

        # Log download
        audit_logger.log_file_operation(
            user_id="system",
            action="file_download",
            file_name=f"{file_id}.xml",
            file_size=temp_path.stat().st_size
        )

        logger.info(f"File download success: filename={file_id}")
        # Return file and clean up
        return FileResponse(
            temp_path,
            media_type="application/xml",
            filename=f"converted_{file_id}.xml",
            background=temp_path.unlink if temp_path != unencrypted_path else None
        )

    except Exception as e:
        logger.error(f"File download failed: filename={file_id}, error={str(e)}")
        audit_logger.log_error(
            user_id="system",
            action="download_file",
            error=e,
            details={"file_id": file_id}
        )
        raise HTTPException(status_code=400, detail=str(e))

def sanitize_xml_tag(name):
    tag = re.sub(r'\s+', '_', name)
    tag = re.sub(r'[^a-zA-Z0-9_.-]', '', tag)
    if not re.match(r'^[a-zA-Z_]', tag):
        tag = '_' + tag
    return tag