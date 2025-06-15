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
        conversion_request = ConversionRequest()
        if request_data:
            try:
                request_dict = json.loads(request_data)
                conversion_request = ConversionRequest(**request_dict)
            except json.JSONDecodeError:
                audit_logger.log_conversion_event(
                    user_id="system",
                    input_file=file.filename,
                    output_file="",
                    conversion_time=0.0,
                    status="error",
                    details={"error": "Invalid request data format"}
                )
                raise HTTPException(status_code=400, detail="Invalid request data format")
            except ValueError as e:
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

        # Save uploaded file
        try:
            content = await file.read()
            with open(input_path, "wb") as f:
                f.write(content)
            
            audit_logger.log_file_operation(
                user_id="system",
                action="save",
                file_name=str(input_path),
                file_size=len(content),
                file_type=Path(file.filename).suffix
            )
        except Exception as e:
            audit_logger.log_file_operation(
                user_id="system",
                action="save",
                file_name=str(input_path),
                file_size=0,
                file_type=Path(file.filename).suffix,
                status="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

        try:
            # Convert file
            converter.convert(
                input_file=input_path,
                output_file=output_path,
                header_fields=conversion_request.header_fields,
                sheet_name=conversion_request.sheet_name
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
                    "header_fields": len(conversion_request.header_fields or {})
                }
            )

            return ConversionResponse(
                status="success",
                message="File converted successfully",
                downloadUrl=download_url
            )

        except (ValueError, FileNotFoundError) as e:
            audit_logger.log_conversion_event(
                user_id="system",
                input_file=file.filename,
                output_file=str(output_path),
                conversion_time=(datetime.now() - start_time).total_seconds(),
                status="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            audit_logger.log_conversion_event(
                user_id="system",
                input_file=file.filename,
                output_file=str(output_path),
                conversion_time=(datetime.now() - start_time).total_seconds(),
                status="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

        finally:
            # Cleanup input file
            if input_path.exists():
                input_path.unlink()
                audit_logger.log_file_operation(
                    user_id="system",
                    action="delete",
                    file_name=str(input_path),
                    file_size=0,
                    file_type=Path(file.filename).suffix
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download converted XML file."""
    start_time = datetime.now()
    try:
        # Check for encrypted file
        encrypted_path = config.OUTPUT_DIR / f"{file_id}.xml.enc"
        if not encrypted_path.exists():
            audit_logger.log_file_operation(
                user_id="system",
                action="download",
                file_name=str(encrypted_path),
                file_size=0,
                file_type=".xml",
                status="error",
                details={"error": "File not found"}
            )
            raise HTTPException(status_code=404, detail="File not found")

        # Create temporary file for decrypted content
        temp_path = config.OUTPUT_DIR / f"temp_{file_id}.xml"
        
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
            background=temp_path.unlink
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