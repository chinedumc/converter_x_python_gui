from pydantic import BaseModel, Field, validator
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from ..config import config

class HeaderField(BaseModel):
    name: str = Field(..., description="Header field name")
    value: str = Field(..., description="Header field value")


class ConversionRequest(BaseModel):
    """Request model for conversion."""
    header_fields: Optional[List[HeaderField]] = None
    sheet_name: Optional[str] = None
    encrypt_output: bool = True
    @validator('header_fields')
    def validate_header_fields(cls, v):
        if v is not None:
            for key in v.keys():
                if not key.replace('_', '').isalnum():
                    raise ValueError(
                        'Header field names must contain only '
                        'alphanumeric characters and underscores'
                    )
        return v

class ConversionResponse(BaseModel):
    status: str = Field(..., description="Conversion status")
    message: str = Field(..., description="Status message")
    file_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the converted file"
    )
    conversion_time: Optional[float] = Field(
        default=None,
        description="Conversion time in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of conversion"
    )

class ErrorResponse(BaseModel):
    status: str = Field(default="error", description="Error status")
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of error"
    )
    details: Optional[str] = Field(
        default=None,
        description="Detailed error information (only shown when SHOW_ERROR_DETAILS is enabled)"
    )

class FileValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="File validation status")
    message: str = Field(..., description="Validation message")
    file_size: Optional[int] = Field(
        default=None,
        description="File size in bytes"
    )
    file_type: Optional[str] = Field(
        default=None,
        description="File type/extension"
    )

    @validator('file_size')
    def validate_file_size(cls, v):
        if v is not None:
            max_size = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if v > max_size:
                raise ValueError(
                    f'File size exceeds maximum limit of '
                    f'{config.MAX_UPLOAD_SIZE_MB}MB'
                )
        return v

    @validator('file_type')
    def validate_file_type(cls, v):
        if v is not None:
            if not Path(f"test{v}").suffix.lower() in config.ALLOWED_EXTENSIONS:
                raise ValueError(
                    f'File type {v} not allowed. Allowed types: '
                    f'{", ".join(config.ALLOWED_EXTENSIONS)}'
                )
        return v

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )