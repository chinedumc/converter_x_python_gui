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

class ExcelToXMLConverter:
    def __init__(self):
        self.namespace = config.XML_NAMESPACE
        self.schema_version = config.XML_SCHEMA_VERSION

    def _sanitize_xml_tag(self, tag: str) -> str:
        """Sanitize XML tag name to ensure it's valid."""
        # Replace spaces and special characters with underscore
        tag = ''.join(c if c.isalnum() or c == '_' else '_' for c in tag)
        # Ensure tag starts with letter or underscore
        if tag and not (tag[0].isalpha() or tag[0] == '_'):
            tag = '_' + tag
        # Remove consecutive underscores
        while '__' in tag:
            tag = tag.replace('__', '_')
        return tag

    def _create_header(self, root: ET.Element, header_fields: Dict[str, str]) -> None:
        """Create XML header section with provided fields."""
        header = ET.SubElement(root, "Header")
        for key, value in header_fields.items():
            # Sanitize and validate tag name
            sanitized_key = self._sanitize_xml_tag(key)
            if not sanitized_key:
                raise ValueError(f"Invalid header field name: {key}")
            field = ET.SubElement(header, sanitized_key)
            field.text = str(value)

        # Add metadata
        metadata = ET.SubElement(header, "Metadata")
        ET.SubElement(metadata, "GeneratedAt").text = datetime.utcnow().isoformat()
        ET.SubElement(metadata, "SchemaVersion").text = self.schema_version

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

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Convert XML element to a pretty-printed string."""
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def convert(self,
        input_file: Path,
        output_file: Path,
        header_fields: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        user_id: str = "system"
    ) -> None:
        """Convert Excel file to XML with optional header fields."""
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

            # Create root element with namespace
            root = ET.Element("ExcelConverter", {"xmlns": self.namespace})

            # Add header section if provided
            if header_fields:
                try:
                    self._create_header(root, header_fields)
                except ValueError as e:
                    raise ValueError(f"Invalid header fields: {str(e)}")

            # Process Excel data
            try:
                records = self._process_excel_data(df)
            except Exception as e:
                raise ValueError(f"Failed to process Excel data: {str(e)}")

            # Create data section
            self._create_data_section(root, records)

            # Convert to pretty-printed XML
            xml_content = self._prettify_xml(root)

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Encrypt the output file
            encrypted_output = output_file.with_suffix('.xml.enc')
            encryption.encrypt_file(output_file, encrypted_output)

            # Calculate conversion time
            conversion_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log successful conversion
            audit_logger.log_conversion_event(
                user_id=user_id,
                input_file=str(input_file),
                output_file=str(encrypted_output),
                conversion_time=conversion_time,
                details={
                    "rows_processed": len(records),
                    "columns": list(df.columns),
                    "sheet_name": sheet_name or "default"
                }
            )

            # Remove unencrypted output file
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
                    "sheet_name": sheet_name
                }
            )
            raise

    def validate_excel_file(self, file_path: Path) -> bool:
        """Validate Excel file format and content."""
        try:
            # Check file extension
            if not config.validate_file_extension(file_path.name):
                return False

            # Try to read the file
            pd.read_excel(file_path)
            return True

        except Exception as e:
            audit_logger.log_error(
                user_id="system",
                action="validate_excel_file",
                error=e,
                details={"file": str(file_path)}
            )
            return False

# Create singleton instance
converter = ExcelToXMLConverter()