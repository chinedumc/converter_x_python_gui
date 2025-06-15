# PowerShell script to build the application for production

# Function to check if a command exists
function Test-Command {
    param ($Command)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'stop'
    try { if (Get-Command $Command) { return $true } }
    catch { return $false }
    finally { $ErrorActionPreference = $oldPreference }
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
if (-not (Test-Command python)) {
    Write-Host "Error: Python is not installed" -ForegroundColor Red
    exit 1
}

# Check Node.js
if (-not (Test-Command node)) {
    Write-Host "Error: Node.js is not installed" -ForegroundColor Red
    exit 1
}

# Check npm
if (-not (Test-Command npm)) {
    Write-Host "Error: npm is not installed" -ForegroundColor Red
    exit 1
}

# Create dist directory
Write-Host "Creating distribution directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path dist

# Function to build backend
function Build-Backend {
    Write-Host "\nBuilding backend..." -ForegroundColor Green
    
    # Create and activate virtual environment
    python -m venv dist\venv
    .\dist\venv\Scripts\Activate

    # Install production dependencies
    pip install -r backend\requirements.txt

    # Copy backend files
    Copy-Item -Path backend\* -Destination dist\backend -Recurse -Force
    
    # Create production .env file
    Copy-Item -Path .env.example -Destination dist\backend\.env

    # Deactivate virtual environment
    deactivate
}

# Function to build frontend
function Build-Frontend {
    Write-Host "\nBuilding frontend..." -ForegroundColor Green
    Set-Location frontend

    # Install dependencies
    npm ci --production

    # Build for production
    npm run build

    # Copy build output to dist
    Copy-Item -Path .next -Destination ..\dist\frontend\.next -Recurse -Force
    Copy-Item -Path public -Destination ..\dist\frontend\public -Recurse -Force
    Copy-Item -Path package.json -Destination ..\dist\frontend\package.json
    Copy-Item -Path next.config.js -Destination ..\dist\frontend\next.config.js

    Set-Location ..
}

# Function to create startup scripts
function Create-StartupScripts {
    Write-Host "\nCreating startup scripts..." -ForegroundColor Green

    # Create start script for Windows
    @"
    @echo off
    echo Starting Excel to XML Converter...
    
    REM Start backend server
    start cmd /k "cd backend && ..\venv\Scripts\activate && python run.py"
    
    REM Start frontend server
    start cmd /k "cd frontend && npm start"
    
    REM Open application in browser
    timeout /t 5
    start http://localhost:3000
"@ | Out-File -FilePath dist\start.bat -Encoding ASCII

    # Create README for deployment
    @"
# Deployment Instructions

## Prerequisites
- Python 3.8+
- Node.js 18+
- npm

## Configuration
1. Update the '.env' file in the backend directory with your production settings
2. Configure SSL certificates if needed

## Starting the Application
1. Run 'start.bat'
2. Access the application at http://localhost:3000

## Ports Used
- Frontend: 3000
- Backend: 8000

## Security Notes
- Ensure all sensitive environment variables are properly set
- Configure firewall rules as needed
- Set up SSL/TLS in production
"@ | Out-File -FilePath dist\DEPLOY.md
}

# Main execution
try {
    # Clean dist directory if it exists
    if (Test-Path dist) {
        Remove-Item -Path dist -Recurse -Force
    }

    # Run security audit
    Write-Host "Running security audit..." -ForegroundColor Yellow
    Set-Location frontend
    npm audit
    Set-Location ..

    # Build components
    Build-Backend
    Build-Frontend
    Create-StartupScripts

    Write-Host "\nBuild completed successfully!" -ForegroundColor Green
    Write-Host "Distribution files are available in the 'dist' directory"
    Write-Host "See 'dist\DEPLOY.md' for deployment instructions"
}
catch {
    Write-Host "\nError occurred during build: $_" -ForegroundColor Red
    exit 1
}