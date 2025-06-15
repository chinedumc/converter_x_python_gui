# Excel to XML Converter

A modern, secure web application for converting Excel files to XML format with advanced features and best practices implementation.

## Features

### Security

- OWASP Top 10 compliance
- AES-256 encryption for file storage
- Secure session management (5-minute timeout)
- Rate limiting and CORS protection
- Input validation and sanitization

### Functionality

- Excel file validation
- Customizable XML header fields
- Progress tracking
- Audit logging
- Mobile responsive UI

### Technical Stack

#### Frontend

- Next.js 13+ with App Router
- TypeScript
- Tailwind CSS
- Progressive Web App (PWA) support
- WCAG accessibility compliance

#### Backend

- FastAPI (Python)
- Python's built-in logging for structured logging
- Pandas for Excel processing
- RESTful API with versioning
- Microservices architecture

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.8+
- npm or yarn

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/converter_x.git
cd converter_x
```

2. Install frontend dependencies:

```bash
cd frontend
npm install
```

3. Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

4. Set up environment variables:

- Copy `.env.example` to `.env`
- Update the values according to your environment

### Running the Application

1. Start the backend server:

```bash
cd backend
python run.py
```

2. Start the frontend development server:

```bash
cd frontend
npm run dev
```

3. Access the application at `http://localhost:3000`

## API Documentation

When running in development mode, API documentation is available at:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Security Features

### Authentication & Authorization

- JWT-based authentication
- 5-minute session timeout
- Rate limiting (100 requests/minute)

### Data Protection

- AES-256 encryption for stored files
- SSL/TLS encryption for data in transit
- Secure file handling and cleanup

### Input Validation

- File type validation (.xls, .xlsx)
- File size limits (configurable)
- XML tag name validation
- Request payload validation

## Logging and Monitoring

### Audit Trail

- User actions
- File operations
- Security events
- Error tracking

### Logging Integration

- Structured logging with Python's logging module
- Daily log rotation with 90-day retention
- Comprehensive error tracking and aggregation

## Development

### Code Style

- ESLint + Prettier (Frontend)
- Black + isort (Backend)
- TypeScript strict mode

### Testing

- Jest for frontend
- pytest for backend
- Integration tests
- Security testing

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FastAPI
- Next.js
- Tailwind CSS
- Python logging
- OWASP
