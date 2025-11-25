const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Validate required environment variables
if (!process.env.SECRET_KEY) {
    console.error('ERROR: SECRET_KEY environment variable is required');
    process.exit(1);
}
if (!process.env.ENCRYPTION_KEY) {
    console.error('ERROR: ENCRYPTION_KEY environment variable is required');
    process.exit(1);
}

// Base directory
const BASE_DIR = __dirname;

// Handle OUTPUT_DIR - resolve relative paths relative to BASE_DIR
let OUTPUT_DIR = process.env.OUTPUT_DIR || path.join(require('os').homedir(), 'converter_x_output');
if (OUTPUT_DIR && !path.isAbsolute(OUTPUT_DIR)) {
    OUTPUT_DIR = path.join(BASE_DIR, OUTPUT_DIR);
}

const LOG_DIR = path.join(BASE_DIR, 'logs');
const UPLOAD_DIR = path.join(BASE_DIR, 'uploads');

// Create necessary directories
[OUTPUT_DIR, LOG_DIR, UPLOAD_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

const config = {
    // API Settings
    API_V1_PREFIX: '/api/v1',
    PROJECT_NAME: 'Excel to XML Converter',
    PORT: parseInt(process.env.PORT || '8000', 10),
    DEBUG: process.env.DEBUG?.toLowerCase() === 'true',

    // Paths
    BASE_DIR,
    OUTPUT_DIR,
    LOG_DIR,
    UPLOAD_DIR,
    LOG_FILE_PATH: path.join(LOG_DIR, 'audit.log'),

    // Security - require these environment variables
    SECRET_KEY: process.env.SECRET_KEY,
    ENCRYPTION_KEY: process.env.ENCRYPTION_KEY,

    // Session
    SESSION_TIMEOUT_MINUTES: parseInt(process.env.SESSION_TIMEOUT_MINUTES || '5', 10),

    // CORS
    ALLOWED_ORIGINS: (process.env.ALLOWED_ORIGINS || 'http://localhost:3000').split(','),

    // File Upload
    MAX_UPLOAD_SIZE_MB: parseInt(process.env.MAX_UPLOAD_SIZE_MB || '10', 10),
    ALLOWED_EXTENSIONS: ['.xls', '.xlsx'],

    // Rate Limiting
    RATE_LIMIT_CALLS: parseInt(process.env.RATE_LIMIT_CALLS || '100', 10),
    RATE_LIMIT_PERIOD: parseInt(process.env.RATE_LIMIT_PERIOD || '60', 10),

    // Logging
    LOG_LEVEL: process.env.LOG_LEVEL || 'info',

    // XML Settings
    XML_NAMESPACE: 'http://www.example.com/xml/converter',
    XML_SCHEMA_VERSION: '1.0',

    // Validation helpers
    validateFileExtension(filename) {
        const ext = path.extname(filename).toLowerCase();
        return this.ALLOWED_EXTENSIONS.includes(ext);
    },

    getUploadPath(filename) {
        return path.join(this.UPLOAD_DIR, filename);
    },

    getOutputPath(filename) {
        return path.join(this.OUTPUT_DIR, filename);
    }
};

module.exports = config;
