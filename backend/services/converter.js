const XLSX = require('xlsx');
const { create } = require('xmlbuilder2');
const fs = require('fs');
const path = require('path');
const config = require('../config');
const { auditLogger } = require('../utils/logger');

class ExcelToXMLConverter {
    constructor() {
        this.namespace = config.XML_NAMESPACE;
        this.schemaVersion = config.XML_SCHEMA_VERSION;
    }

    /**
     * Sanitize XML tag name to ensure it's valid
     */
    sanitizeXmlTag(tag) {
        if (!tag) {
            return 'EMPTY_TAG';
        }

        // Convert to string and trim
        tag = String(tag).trim();

        // Replace spaces with underscores
        tag = tag.replace(/\s+/g, '_');

        // Remove invalid characters (allow only letters, digits, underscore, hyphen, period)
        tag = tag.replace(/[^a-zA-Z0-9_.-]/g, '');

        // Ensure tag starts with a letter or underscore
        if (!/^[a-zA-Z_]/.test(tag)) {
            tag = '_' + tag;
        }

        // If tag is empty after sanitization, use a fallback
        if (!tag) {
            tag = 'EMPTY_TAG';
        }

        return tag;
    }

    /**
     * Validate Excel file format and content
     */
    validateExcelFile(filePath) {
        try {
            // Check if file exists
            if (!fs.existsSync(filePath)) {
                return false;
            }

            // Check file extension
            const ext = path.extname(filePath).toLowerCase();
            if (!config.ALLOWED_EXTENSIONS.includes(ext)) {
                return false;
            }

            // Try to read the file
            const workbook = XLSX.readFile(filePath);
            
            // Check if there's at least one sheet
            if (!workbook.SheetNames || workbook.SheetNames.length === 0) {
                return false;
            }

            // Get first sheet data
            const sheetName = workbook.SheetNames[0];
            const sheet = workbook.Sheets[sheetName];
            const data = XLSX.utils.sheet_to_json(sheet);

            // Check if file has data
            if (!data || data.length === 0) {
                return false;
            }

            return true;
        } catch (error) {
            auditLogger.logError('system', 'validate_excel_file', error, { file: filePath });
            return false;
        }
    }

    /**
     * Convert Excel file to XML with optional header fields
     */
    convert(inputFile, outputFile, headerFields = {}, sheetName = null, userId = 'system') {
        const startTime = Date.now();

        try {
            // Validate input file exists
            if (!fs.existsSync(inputFile)) {
                throw new Error(`Input file not found: ${inputFile}`);
            }

            // Read Excel file
            const workbook = XLSX.readFile(inputFile);
            
            // Get the appropriate sheet
            const targetSheetName = sheetName || workbook.SheetNames[0];
            if (!workbook.SheetNames.includes(targetSheetName)) {
                throw new Error(`Sheet '${targetSheetName}' not found in Excel file`);
            }

            const sheet = workbook.Sheets[targetSheetName];
            const data = XLSX.utils.sheet_to_json(sheet);

            if (!data || data.length === 0) {
                throw new Error('Excel file is empty');
            }

            // Build XML structure
            const root = create({ version: '1.0', encoding: 'UTF-8' })
                .ele('CALLREPORT');

            // Add header section if header fields are provided
            if (headerFields && Object.keys(headerFields).length > 0) {
                const header = root.ele('HEADER');
                for (const [key, value] of Object.entries(headerFields)) {
                    const tagName = this.sanitizeXmlTag(key);
                    header.ele(tagName).txt(String(value || ''));
                }
            }

            // Create BODY section
            const body = root.ele('BODY');

            // Convert each row to XML
            for (const row of data) {
                const record = body.ele('CALLREPORT_DATA');
                for (const [column, cellValue] of Object.entries(row)) {
                    const tagName = this.sanitizeXmlTag(column);
                    const value = this.formatCellValue(cellValue);
                    record.ele(tagName).txt(value);
                }
            }

            // Convert to pretty-printed XML string
            const xmlContent = root.end({ prettyPrint: true });

            // Write to output file
            fs.writeFileSync(outputFile, xmlContent, 'utf-8');

            // Calculate conversion time
            const conversionTime = Date.now() - startTime;

            // Log successful conversion
            auditLogger.logConversionEvent(
                userId,
                inputFile,
                outputFile,
                conversionTime,
                'success',
                {
                    rows_processed: data.length,
                    columns: Object.keys(data[0] || {}),
                    sheet_name: targetSheetName
                }
            );

            return {
                success: true,
                rowsProcessed: data.length,
                conversionTime
            };

        } catch (error) {
            // Log conversion error
            auditLogger.logError(userId, 'convert_excel_to_xml', error, {
                input_file: inputFile,
                output_file: outputFile,
                sheet_name: sheetName
            });
            throw error;
        }
    }

    /**
     * Format cell value for XML output
     */
    formatCellValue(value) {
        if (value === null || value === undefined) {
            return '';
        }

        if (value instanceof Date) {
            return value.toISOString();
        }

        if (typeof value === 'number') {
            return String(value);
        }

        return String(value);
    }

    /**
     * Get file info from Excel file
     */
    getFileInfo(filePath) {
        try {
            const workbook = XLSX.readFile(filePath);
            const sheetName = workbook.SheetNames[0];
            const sheet = workbook.Sheets[sheetName];
            const data = XLSX.utils.sheet_to_json(sheet);

            return {
                sheetNames: workbook.SheetNames,
                rowCount: data.length,
                columns: Object.keys(data[0] || {})
            };
        } catch (error) {
            throw new Error(`Failed to read Excel file: ${error.message}`);
        }
    }
}

// Create singleton instance
const converter = new ExcelToXMLConverter();

module.exports = { converter, ExcelToXMLConverter };
