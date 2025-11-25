const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const config = require('../config');
const { converter } = require('../services/converter');
const { auditLogger } = require('../utils/logger');

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, config.UPLOAD_DIR);
    },
    filename: (req, file, cb) => {
        const fileId = uuidv4();
        const ext = path.extname(file.originalname);
        cb(null, `${fileId}_input${ext}`);
    }
});

const fileFilter = (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (config.ALLOWED_EXTENSIONS.includes(ext)) {
        cb(null, true);
    } else {
        cb(new Error('Invalid file type. Only .xls and .xlsx files are allowed'), false);
    }
};

const upload = multer({
    storage,
    fileFilter,
    limits: {
        fileSize: config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    }
});

// Health check endpoint
router.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        version: config.XML_SCHEMA_VERSION,
        timestamp: new Date().toISOString()
    });
});

// Validate file endpoint
router.post('/validate', upload.single('file'), async (req, res) => {
    const startTime = Date.now();
    let uploadedFilePath = null;

    try {
        if (!req.file) {
            return res.status(400).json({
                is_valid: false,
                message: 'No file uploaded'
            });
        }

        uploadedFilePath = req.file.path;
        const fileSize = req.file.size;
        const fileType = path.extname(req.file.originalname);

        auditLogger.logFileOperation(
            'system',
            'upload',
            req.file.originalname,
            fileSize
        );

        // Validate file size
        if (fileSize > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
            return res.json({
                is_valid: false,
                message: `File size exceeds ${config.MAX_UPLOAD_SIZE_MB}MB limit`,
                file_size: fileSize,
                file_type: fileType
            });
        }

        // Validate file type
        if (!config.validateFileExtension(req.file.originalname)) {
            return res.json({
                is_valid: false,
                message: 'Invalid file type. Only .xls and .xlsx files are allowed',
                file_size: fileSize,
                file_type: fileType
            });
        }

        // Validate Excel content
        const isValid = converter.validateExcelFile(uploadedFilePath);

        res.json({
            is_valid: isValid,
            message: isValid ? 'File is valid' : 'Invalid Excel file format',
            file_size: fileSize,
            file_type: fileType
        });

    } catch (error) {
        auditLogger.logError('system', 'validate_file', error, {
            filename: req.file?.originalname
        });
        res.status(400).json({
            is_valid: false,
            message: error.message
        });
    } finally {
        // Clean up uploaded file
        if (uploadedFilePath && fs.existsSync(uploadedFilePath)) {
            fs.unlinkSync(uploadedFilePath);
        }
    }
});

// Convert file endpoint
router.post('/convert', upload.single('file'), async (req, res) => {
    const startTime = Date.now();
    let inputPath = null;
    let outputPath = null;
    let outputFilename = null;

    try {
        if (!req.file) {
            return res.status(400).json({
                status: 'error',
                message: 'No file uploaded'
            });
        }

        inputPath = req.file.path;
        const fileSize = req.file.size;

        auditLogger.logFileOperation(
            'system',
            'upload',
            req.file.originalname,
            fileSize
        );

        // Parse header fields from request
        // Supports two formats:
        // 1. 'header_fields': Direct array of {tagName, tagValue} objects (from excel-to-xml-converter.tsx)
        // 2. 'request_data': JSON with header_fields inside (from lib/api.ts)
        let headerFields = {};
        const headerFieldsRaw = req.body.header_fields || req.body.request_data;
        
        if (headerFieldsRaw) {
            try {
                let parsed = JSON.parse(headerFieldsRaw);
                
                // Handle array format (from frontend)
                if (Array.isArray(parsed)) {
                    for (const field of parsed) {
                        if (field.tagName && field.tagValue !== undefined) {
                            const tagName = field.tagName.replace(/\s+/g, '_');
                            headerFields[tagName] = field.tagValue;
                        }
                    }
                } else if (parsed.header_fields && Array.isArray(parsed.header_fields)) {
                    // Handle nested format
                    for (const field of parsed.header_fields) {
                        if (field.tagName && field.tagValue !== undefined) {
                            const tagName = field.tagName.replace(/\s+/g, '_');
                            headerFields[tagName] = field.tagValue;
                        }
                    }
                } else {
                    // Handle object format
                    headerFields = parsed;
                }
            } catch (e) {
                auditLogger.logError('system', 'parse_header_fields', e, {
                    raw_data: headerFieldsRaw
                });
            }
        }

        // Generate output file info
        const fileId = uuidv4();
        outputFilename = `${fileId}_output.xml`;
        outputPath = path.join(config.OUTPUT_DIR, outputFilename);

        // Parse sheet name if provided
        let sheetName = null;
        if (req.body.request_data) {
            try {
                const requestData = JSON.parse(req.body.request_data);
                sheetName = requestData.sheet_name;
            } catch (e) {
                // Ignore parsing errors for sheet name
            }
        }

        // Convert file
        converter.convert(
            inputPath,
            outputPath,
            headerFields,
            sheetName,
            'system'
        );

        // Generate download URL
        const downloadUrl = `${config.API_V1_PREFIX}/download/${fileId}`;

        // Log successful conversion
        const conversionTime = Date.now() - startTime;
        auditLogger.logConversionEvent(
            'system',
            req.file.originalname,
            outputPath,
            conversionTime,
            'success',
            {
                input_size: fileSize,
                output_size: fs.existsSync(outputPath) ? fs.statSync(outputPath).size : 0,
                header_fields: Object.keys(headerFields).length
            }
        );

        res.json({
            status: 'success',
            message: 'File converted successfully',
            downloadUrl
        });

    } catch (error) {
        auditLogger.logError('system', 'convert_file', error, {
            filename: req.file?.originalname
        });
        res.status(500).json({
            status: 'error',
            message: error.message || 'An error occurred during the conversion process'
        });
    } finally {
        // Clean up input file
        if (inputPath && fs.existsSync(inputPath)) {
            fs.unlinkSync(inputPath);
        }
    }
});

// Download file endpoint
router.get('/download/:fileId', async (req, res) => {
    try {
        const { fileId } = req.params;
        
        // Look for the output file
        const xmlPath = path.join(config.OUTPUT_DIR, `${fileId}_output.xml`);
        
        if (!fs.existsSync(xmlPath)) {
            auditLogger.logFileOperation(
                'system',
                'download',
                `${fileId}.xml`,
                0,
                'error',
                { error: 'File not found' }
            );
            return res.status(404).json({
                status: 'error',
                message: 'File not found'
            });
        }

        const fileSize = fs.statSync(xmlPath).size;
        
        auditLogger.logFileOperation(
            'system',
            'file_download',
            `${fileId}.xml`,
            fileSize
        );

        // Send file and delete after sending
        res.download(xmlPath, `converted_${fileId}.xml`, (err) => {
            // Delete the file after sending (or on error)
            if (fs.existsSync(xmlPath)) {
                fs.unlinkSync(xmlPath);
            }
            if (err && !res.headersSent) {
                res.status(500).json({
                    status: 'error',
                    message: 'Error downloading file'
                });
            }
        });

    } catch (error) {
        auditLogger.logError('system', 'download_file', error, {
            file_id: req.params.fileId
        });
        res.status(400).json({
            status: 'error',
            message: error.message
        });
    }
});

module.exports = router;
