# Excel-to-XML Converter Web Application

## 🚀 Overview

A modern, secure, and responsive web-based application that allows users to upload Excel files, define custom XML headers, and convert the content into a downloadable XML file. Designed with clean architecture, modular code, and built-in OWASP Top 10 security protections.

---

## 📐 Architecture

### Frontend (UI/UX)
- **Framework**: Next.js
- **Styling**: Tailwind CSS
- **Features**:
  - Mobile responsive (phones and tablets)
  - Component-based design
  - PWA support
  - Cross-browser compatibility
  - WCAG-compliant accessibility
  - Theme: Gradient wine-red, black, and white

---

## 🧩 Functional Features

### Menu Structure
1. Input XML header (dynamic input)
2. Upload Excel file
3. Click to start conversion
4. Display conversion progress
5. Show completion message
6. Download converted XML
7. Select folder for saving XML (where supported)

---

### 🧾 XML Header Builder

Users can dynamically define the `<HEADER>` section of the resulting XML file using blank input fields.

#### Example UI Behavior:
- For each XML field:
  - **Tag Name** input → e.g., `CALLREPORT_ID`
  - **Tag Value** input → e.g., `DTR001`

This pair will produce:
```xml
<CALLREPORT_ID>DTR001</CALLREPORT_ID>
```

#### Full Header Example:
```xml
<HEADER>
  <CALLREPORT_ID>DTR001</CALLREPORT_ID>
  <CALLREPORT_DESC>DAILY INWARD MONEY TRANSFER</CALLREPORT_DESC>
  <INST_CODE>00232</INST_CODE>
  <INST_NAME>STERLING BANK</INST_NAME>
  <AS_AT>30-04-2025</AS_AT>
</HEADER>
```

#### Features:
- **"Add More" Button**: Adds new input pairs (Tag Name + Tag Value) for the user to continue building the XML header.
- **Validation**: Ensure tag names follow XML naming rules and values are not empty.
- **Preview**: Optional live preview of the resulting `<HEADER>` block.

---

## Backend Implementation

- **Language**: Python
- **Architecture**:
  - Microservices
  - RESTful API
  - Service layer + Repository pattern
  - Event-driven architecture for conversion tasks

---

## 🔐 Security & Compliance

### Application Security
- AES-256 encryption for sensitive data
- SSL/TLS for secure transmission
- Input validation
- XSS, CSRF, SQL Injection prevention
- Session timeout after 5 minutes of inactivity

### Data Protection
- Encrypted data at rest
- Regular backups
- GDPR-compliant data policies
- Data retention enforcement

---

## 📊 Logging & Auditing

- **Logger**: Python's built-in logging module
- Tracks:
  - Exceptions and errors
  - User actions
  - System changes
  - Access logs
  - Security incidents

---

## 🔁 API Management

- RESTful endpoints
- Token-based authentication
- Rate limiting
- Versioning
- CORS management

---

## 🏗️ Setup Instructions (Basic Scaffold)

1. **Frontend**
   - Initialize a Next.js project
   - Install Tailwind CSS
   - Create base components:
     - `HeaderFieldBuilder` – Dynamic field generator for XML header
     - `ExcelUploader`
     - `ConvertButton`
     - `ProgressIndicator`
     - `DownloadButton`
     - `SaveLocationSelector`

2. **Backend**
   - Set up Python backend using FastAPI or Flask
   - Create API endpoints:
     - `POST /convert`
     - `GET /download/:id`
   - Integrate AES-256 encryption utility
   - Add session timeout management
   - Setup structured logging with Serilog

---

## 📦 Optional Enhancements

- Drag-and-drop Excel uploader
- XML schema validation (XSD support)
- Multilingual UI (localization support)

---

## 🧪 Development Goals

Start with building the **basic structure**:
- Page layout and navigation
- API endpoints with stubbed logic
- Placeholder components for UI
- Security middleware and logger setup

---

## 📁 Folder Structure (Suggestion)

```
/excel-to-xml-converter/
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── public/
│   └── styles/
├── backend/
│   ├── services/
│   ├── controllers/
│   ├── models/
│   └── utils/
└── README.md
```

---

## 📄 License

MIT License – free to use, modify, and distribute.