const winston = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('../config');

// Ensure log directory exists
if (!fs.existsSync(config.LOG_DIR)) {
    fs.mkdirSync(config.LOG_DIR, { recursive: true });
}

// Create Winston logger
const logger = winston.createLogger({
    level: config.LOG_LEVEL.toLowerCase(),
    format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({
            filename: config.LOG_FILE_PATH,
            maxsize: 20 * 1024 * 1024, // 20MB
            maxFiles: 30
        }),
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.simple()
            )
        })
    ]
});

// Audit logger class
class AuditLogger {
    constructor() {
        this.logger = logger;
    }

    _formatMessage(eventType, userId, action, details = {}, status = 'success') {
        return {
            timestamp: new Date().toISOString(),
            event_type: eventType,
            user_id: userId,
            action: action,
            status: status,
            details: details
        };
    }

    logAuthEvent(userId, action, status = 'success', details = {}) {
        const message = this._formatMessage('authentication', userId, action, details, status);
        if (status === 'success') {
            this.logger.info(message);
        } else {
            this.logger.warn(message);
        }
    }

    logFileOperation(userId, action, fileName, fileSize, status = 'success', details = {}) {
        const fileDetails = {
            file_name: fileName,
            file_size: fileSize,
            ...details
        };
        const message = this._formatMessage('file_operation', userId, action, fileDetails, status);
        if (status === 'success') {
            this.logger.info(message);
        } else {
            this.logger.error(message);
        }
    }

    logConversionEvent(userId, inputFile, outputFile, conversionTime, status = 'success', details = {}) {
        const conversionDetails = {
            input_file: inputFile,
            output_file: outputFile,
            conversion_time_ms: conversionTime,
            ...details
        };
        const message = this._formatMessage('conversion', userId, 'convert_excel_to_xml', conversionDetails, status);
        if (status === 'success') {
            this.logger.info(message);
        } else {
            this.logger.error(message);
        }
    }

    logSecurityEvent(userId, action, ipAddress, status = 'success', details = {}) {
        const securityDetails = {
            ip_address: ipAddress,
            ...details
        };
        const message = this._formatMessage('security', userId, action, securityDetails, status);
        if (status === 'success') {
            this.logger.info(message);
        } else {
            this.logger.warn(message);
        }
    }

    logError(userId, action, error, details = {}) {
        const errorDetails = {
            error_type: error.name || 'Error',
            error_message: error.message || String(error),
            ...details
        };
        const message = this._formatMessage('error', userId, action, errorDetails, 'error');
        this.logger.error(message);
    }

    info(message) {
        this.logger.info(message);
    }

    error(message) {
        this.logger.error(message);
    }

    warn(message) {
        this.logger.warn(message);
    }
}

const auditLogger = new AuditLogger();

module.exports = { logger, auditLogger };
