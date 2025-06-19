import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from ..config import config
from ..utils.audit import audit_logger
from ..utils.encryption import encryption
import time
import logging

log = logging.getLogger(__name__)

class ExcelToXMLConverter:
    def __init__(self):
        self.namespace = config.XML_NAMESPACE
        self.schema_version = config.XML_SCHEMA_VERSION

    def _sanitize_xml_tag(self, tag: str) -> str:
        """Validate XML tag name."""
        if not tag:
            raise ValueError("Empty tag name is not allowed")
            
        # Convert to string and trim
        tag = str(tag).strip()
        
        # Check for special characters
        special_chars = set(tag) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        if special_chars:
            raise ValueError(f"Invalid characters in tag name: {tag}. Special characters {special_chars} are not allowed")
            
        # Replace spaces with underscores
        tag = tag.replace(' ', '_')
        
        # Ensure tag starts with letter or underscore
        if not (tag[0].isalpha() or tag[0] == '_'):
            tag = '_' + tag
            
        # Remove consecutive underscores and trailing underscores
        while '__' in tag:
            tag = tag.replace('__', '_')
        tag = tag.strip('_')
        
        # Ensure tag is not empty after sanitization
        if not tag:
            raise ValueError("Tag name cannot be empty after sanitization")
            
        return tag

    def _create_header(self, root: ET.Element, header_fields: Dict[str, str]) -> None:
        """Create XML header section with provided fields."""
        if not header_fields:
            return  # Skip header creation if no fields provided

        # Create HEADER element
        header = ET.SubElement(root, "HEADER")
        
        # Add each header field
        for key, value in header_fields.items():
            try:
                # Create field element with exact name from user input
                # Replace spaces with underscores to maintain valid XML
                tag_name = key.replace(' ', '_')
                field = ET.SubElement(header, tag_name)
                
                # Set value without sanitization
                if value is not None:
                    field.text = str(value)
                else:
                    field.text = ""
                    
            except Exception as e:
                log.error(f"Error processing header field {key}: {str(e)}")
                raise ValueError(f"Error processing header field: {str(e)}")

    def _process_excel_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Process Excel data and handle various data types."""
        records = []
        for _, row in df.iterrows():
            record = {}
            for column in df.columns:
                value = row[column]
                # Handle different data types
                if pd.isna(value):
                    record[column] = ""
                elif isinstance(value, (int, float)):
                    record[column] = str(value)
                elif isinstance(value, datetime):
                    record[column] = value.isoformat()
                else:
                    record[column] = str(value)
            records.append(record)
        return records

    def _create_data_section(self, root: ET.Element, records: List[Dict[str, Any]]) -> None:
        """Create XML data section from processed records."""
        data = ET.SubElement(root, "Data")
        for record in records:
            row = ET.SubElement(data, "Row")
            for field_name, value in record.items():
                # Sanitize and validate field name
                sanitized_name = self._sanitize_xml_tag(field_name)
                if not sanitized_name:
                    continue
                field = ET.SubElement(row, sanitized_name)
                field.text = value

    def _prettify_xml(self, xml_content: str) -> str:
        """Prettify XML content."""
        parsed = minidom.parseString(xml_content)
        return parsed.toprettyxml(indent='  ')

    def convert(self,
        input_file: Path,
        output_file: Path,
        header_fields: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        encrypt_output: bool = True,
        user_id: str = "system"
    ) -> None:
        """Convert Excel file to XML with optional header fields and encryption."""
        start_time = time.time()

        try:
            # Validate input file exists
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")

            # Read Excel file
            try:
                df = pd.read_excel(input_file, sheet_name=sheet_name)
            except Exception as e:
                raise ValueError(f"Failed to read Excel file: {str(e)}")

            if df.empty:
                raise ValueError("Excel file is empty")

            # Create root element
            root = ET.Element("CALLREPORT")
            
            # Add header fields if provided
            if header_fields:
                try:
                    log.info(f"Processing header fields: {header_fields}")
                    self._create_header(root, header_fields)
                except ValueError as e:
                    raise ValueError(f"Invalid header fields: {str(e)}")

            # Create BODY element
            body = ET.SubElement(root, "BODY")
            
            # Process Excel data
            try:
                records = self._process_excel_data(df)
            except Exception as e:
                raise ValueError(f"Failed to process Excel data: {str(e)}")

            # Create data section
            self._create_data_section(root, records)

            # Convert to pretty-printed XML
            xml_content = self._prettify_xml(ET.tostring(root, encoding='unicode'))

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Encrypt the output file if requested
            if encrypt_output:
                encrypted_output = output_file.with_suffix('.xml.enc')
                encryption.encrypt_file(output_file, encrypted_output)
                final_output = encrypted_output
            else:
                final_output = output_file

            # Calculate conversion time
            conversion_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log successful conversion
            audit_logger.log_conversion_event(
                user_id=user_id,
                input_file=str(input_file),
                output_file=str(final_output),
                conversion_time=conversion_time,
                details={
                    "rows_processed": len(records),
                    "columns": list(df.columns),
                    "sheet_name": sheet_name or "default",
                    "encrypted": encrypt_output
                }
            )

            # Remove unencrypted file if encryption was applied
            if encrypt_output:
                output_file.unlink()

        except Exception as e:
            # Log conversion error
            audit_logger.log_error(
                user_id=user_id,
                action="convert_excel_to_xml",
                error=e,
                details={
                    "input_file": str(input_file),
                    "output_file": str(output_file),
                    "sheet_name": sheet_name,
                    "encrypted": encrypt_output
                }
            )
            raise

    def validate_excel_file(self, file_path: Path) -> bool:
        """Validate Excel file format and content."""
        try:
            # Check file extension
            if not config.validate_file_extension(file_path.name):
                log.error(f"Invalid file extension: {file_path.suffix}")
                return False

            # Try to read the file
            df = pd.read_excel(file_path)

            # Check if file is empty
            if df.empty:
                log.error("Excel file is empty")
                return False

            # Check for required columns based on CALLREPORT structure
            required_columns = ['SN', 'BRANCH_CODE', 'DEAL_NO', 'UNIQUE_ID', 'CIF_NO1', 'NUBAN', 
                              'NAME', 'DEAL_AMOUNT', 'PRINCIPAL_OUTSTANDING', 'PAST_DUE_BALANCE', 
                              'TOTAL_EXPOSURE', 'PAST_DUE_DAYS', 'VALUE_DATE', 'MATURITY_DATE', 
                              'BVN', 'CRMS_CODE']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                log.error(f"Missing required columns: {missing_columns}")
                return False

            # Validate data types and formats
            data_type_rules = {
                'SN': {'type': 'int'},
                'BRANCH_CODE': {'type': 'int'},
                'DEAL_NO': {'type': 'int'},
                'UNIQUE_ID': {'type': 'str'},
                'CIF_NO1': {'type': 'int'},
                'NUBAN': {'type': 'float'},
                'NAME': {'type': 'str'},
                'DEAL_AMOUNT': {'type': 'float'},
                'PRINCIPAL_OUTSTANDING': {'type': 'float'},
                'PAST_DUE_BALANCE': {'type': 'float'},
                'TOTAL_EXPOSURE': {'type': 'float'},
                'PAST_DUE_DAYS': {'type': 'int'},
                'VALUE_DATE': {'type': 'datetime'},
                'MATURITY_DATE': {'type': 'datetime'},
                'BVN': {'type': 'str'},
                'CRMS_CODE': {'type': 'str'}
            }

            for column, rules in data_type_rules.items():
                try:
                    # Convert column to expected type
                    if rules['type'] == 'int':
                        df[column] = pd.to_numeric(df[column], downcast='integer')
                    elif rules['type'] == 'float':
                        df[column] = pd.to_numeric(df[column], downcast='float')
                    elif rules['type'] == 'datetime':
                        df[column] = pd.to_datetime(df[column])
                    elif rules['type'] == 'str':
                        df[column] = df[column].astype(str)
                except Exception as e:
                    log.error(f"Data type validation failed for column {column}: {str(e)}")
                    return False

                # Check for empty values
                if df[column].isnull().any():
                    log.error(f"Column {column} contains empty values")
                    return False

            return True

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="validate_excel_file",
                error=e,
                details={"file": str(file_path)}
            )
            log.error(f"Excel validation failed: {str(e)}")
            return False

# Create singleton instance
converter = ExcelToXMLConverter()