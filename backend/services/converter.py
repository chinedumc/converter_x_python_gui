import pandas as pd
from typing import Dict, Any
from cryptography.fernet import Fernet
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
from dotenv import load_dotenv
import logging
import re

# Load environment variables
load_dotenv()

# Initialize logger
log = logging.getLogger("converter")

class ExcelToXMLConverter:
    def __init__(self):
        # Initialize encryption key
        self.encryption_key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
        self.cipher_suite = Fernet(self.encryption_key)
        
    def validate_excel(self, file_path: str) -> bool:
        """Validate Excel file format and content."""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Basic validation checks
            if df.empty:
                raise ValueError("Excel file is empty")
                
            # No required columns check; accept any columns
            return True
            
        except Exception as e:
            log.error(f"Excel validation failed: {str(e)}")
            raise ValueError(f"Invalid Excel file: {str(e)}")
    
    def encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data using AES-256."""
        try:
            return self.cipher_suite.encrypt(data.encode())
        except Exception as e:
            log.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt encrypted data."""
        try:
            return self.cipher_suite.decrypt(encrypted_data).decode()
        except Exception as e:
            log.error(f"Decryption failed: {str(e)}")
            raise
    
    def sanitize_xml_tag(self, name: str) -> str:
        """Sanitize XML tag name to ensure it's valid."""
        # Replace spaces and special characters with underscores
        tag = re.sub(r'[\s\W]+', '_', name)
        # Remove leading digits or invalid characters
        tag = re.sub(r'^[^a-zA-Z_]', '_', tag)
        # Remove any remaining invalid characters
        tag = re.sub(r'[^a-zA-Z0-9_.-]', '', tag)
        return tag

    def create_xml_header(self, header_fields: Dict[str, Any]) -> ET.Element:
        """Create XML header section from provided fields."""
        header = ET.Element("HEADER")
        
        try:
            for tag_name, tag_value in header_fields.items():
                # Sanitize and validate tag name
                sanitized_tag = self.sanitize_xml_tag(tag_name)
                if not sanitized_tag:
                    raise ValueError(f"Invalid tag name: {tag_name}")
                    
                element = ET.SubElement(header, sanitized_tag)
                element.text = str(tag_value)
                
            return header
            
        except Exception as e:
            log.error(f"Failed to create XML header: {str(e)}")
            raise
    
    def convert_to_xml(self, excel_path: str, header_fields: Dict[str, Any]) -> str:
        """Convert Excel file to XML with custom header."""
        try:
            # Validate Excel file
            self.validate_excel(excel_path)
            
            # Create root element
            root = ET.Element("ROOT")
            
            # Add header
            converter = ExcelToXMLConverter()
            converter._create_header(root, header_fields)
            
            # Read Excel data
            df = pd.read_excel(excel_path)
            
            # Create data section
            data_section = ET.SubElement(root, "DATA")
            
            # Convert each row to XML
            for _, row in df.iterrows():
                record = ET.SubElement(data_section, "RECORD")
                for column in df.columns:
                    # Skip empty values
                    if pd.isna(row[column]):
                        continue
                        
                    field = ET.SubElement(record, column.upper())
                    field.text = str(row[column])
            
            # Pretty print XML
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            
            # Log success
            log.info("Excel to XML conversion completed successfully")
            
            return xml_str
            
        except Exception as e:
            log.error(f"Conversion failed: {str(e)}")
            raise
    
    def save_xml(self, xml_content: str, output_path: str) -> str:
        """Save XML content to file with encryption."""
        try:
            # Encrypt XML content
            encrypted_content = self.encrypt_data(xml_content)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"converted_{timestamp}.xml.enc"
            full_path = os.path.join(output_path, filename)
            
            # Save encrypted content
            with open(full_path, "wb") as f:
                f.write(encrypted_content)
            
            log.info(f"XML file saved successfully: {filename}")
            return filename
            
        except Exception as e:
            log.error(f"Failed to save XML file: {str(e)}")
            raise