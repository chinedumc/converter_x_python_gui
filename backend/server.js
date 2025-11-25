const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const config = require('./config');
const converterRoutes = require('./routes/converter');
const { auditLogger } = require('./utils/logger');

// Create Express app
const app = express();

// Trust proxy for rate limiting behind reverse proxies
app.set('trust proxy', 1);

// CORS configuration
app.use(cors({
    origin: config.ALLOWED_ORIGINS,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: config.RATE_LIMIT_PERIOD * 1000, // Convert to milliseconds
    max: config.RATE_LIMIT_CALLS,
    message: { detail: 'Too many requests' },
    standardHeaders: true,
    legacyHeaders: false
});

app.use(limiter);

// Parse JSON bodies
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging middleware
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        if (config.DEBUG) {
            auditLogger.info({
                method: req.method,
                path: req.path,
                status: res.statusCode,
                duration: `${duration}ms`
            });
        }
    });
    next();
});

// Root endpoint
app.get('/', (req, res) => {
    res.json({ message: 'Backend is running' });
});

// API routes
app.use(config.API_V1_PREFIX, converterRoutes);

// Error handling middleware
app.use((err, req, res, next) => {
    auditLogger.logError(
        'system',
        'unhandled_error',
        err,
        { path: req.path }
    );

    const showDetails = process.env.SHOW_ERROR_DETAILS?.toLowerCase() === 'true';
    
    res.status(err.status || 500).json({
        message: showDetails ? err.message : 'Internal server error',
        error_code: 'INTERNAL_ERROR',
        timestamp: new Date().toISOString(),
        details: showDetails ? err.stack : undefined
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        message: 'Not found',
        error_code: 'NOT_FOUND',
        timestamp: new Date().toISOString()
    });
});

// Start server
const PORT = config.PORT;

app.listen(PORT, '0.0.0.0', () => {
    auditLogger.logSecurityEvent(
        'system',
        'application_startup',
        'localhost',
        'success',
        {
            version: config.XML_SCHEMA_VERSION,
            debug_mode: config.DEBUG,
            port: PORT
        }
    );
    console.log(`Server running on port ${PORT}`);
    console.log(`API available at http://localhost:${PORT}${config.API_V1_PREFIX}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    auditLogger.logSecurityEvent(
        'system',
        'application_shutdown',
        'localhost'
    );
    process.exit(0);
});

process.on('SIGINT', () => {
    auditLogger.logSecurityEvent(
        'system',
        'application_shutdown',
        'localhost'
    );
    process.exit(0);
});

module.exports = app;
