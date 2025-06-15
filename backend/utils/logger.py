import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
from typing import Any, Dict, Optional
import json
from datetime import datetime

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """Configure and return a logger instance."""
    # Create logs directory if it doesn't exist
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create handlers
    handler = TimedRotatingFileHandler(
        log_file,
        when='D',  # Daily rotation
        interval=1,
        backupCount=90,  # Keep 90 days of logs
        encoding='utf-8'
    )

    # Create formatters and add it to handlers
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(handler)

    return logger

class AuditLogger:
    def __init__(self):
        from ..config import Config
        self.logger = setup_logger("audit", Config.LOG_FILE_PATH)

    def _format_message(self, 
        event_type: str,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> str:
        """Format audit log message in a structured way."""
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "status": status,
            "details": details or {}
        }
        return json.dumps(audit_data)

    def log_auth_event(self,
        user_id: str,
        action: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authentication related events."""
        message = self._format_message(
            "authentication",
            user_id,
            action,
            details,
            status
        )
        if status == "success":
            self.logger.info(message)
        else:
            self.logger.warning(message)

    def log_file_operation(self,
        user_id: str,
        action: str,
        file_name: str,
        file_size: int,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log file operation events."""
        file_details = {
            "file_name": file_name,
            "file_size": file_size,
            **(details or {})
        }
        message = self._format_message(
            "file_operation",
            user_id,
            action,
            file_details,
            status
        )
        if status == "success":
            self.logger.info(message)
        else:
            self.logger.error(message)

    def log_conversion_event(self,
        user_id: str,
        input_file: str,
        output_file: str,
        conversion_time: float,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log file conversion events."""
        conversion_details = {
            "input_file": input_file,
            "output_file": output_file,
            "conversion_time_ms": conversion_time,
            **(details or {})
        }
        message = self._format_message(
            "conversion",
            user_id,
            "convert_excel_to_xml",
            conversion_details,
            status
        )
        if status == "success":
            self.logger.info(message)
        else:
            self.logger.error(message)

    def log_security_event(self,
        user_id: str,
        action: str,
        ip_address: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log security related events."""
        security_details = {
            "ip_address": ip_address,
            **(details or {})
        }
        message = self._format_message(
            "security",
            user_id,
            action,
            security_details,
            status
        )
        if status == "success":
            self.logger.info(message)
        else:
            self.logger.warning(message)

    def log_error(self,
        user_id: str,
        action: str,
        error: Exception,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error events."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(details or {})
        }
        message = self._format_message(
            "error",
            user_id,
            action,
            error_details,
            "error"
        )
        self.logger.error(message)

# Create singleton instance
audit_logger = AuditLogger()