# PowerShell script to run development servers

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
Write-Host "Checking prerequisites..."

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

# Create and activate Python virtual environment
Write-Host "Setting up Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
}

# Activate virtual environment
.\venv\Scripts\Activate

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r backend\requirements.txt

# Install Node.js dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..

# Function to start the backend server
function Start-Backend {
    Write-Host "Starting backend server..." -ForegroundColor Green
    Set-Location backend
    python run.py
}

# Function to start the frontend server
function Start-Frontend {
    Write-Host "Starting frontend server..." -ForegroundColor Green
    Set-Location frontend
    npm run dev
}

# Start both servers
Write-Host "Starting development servers..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; Start-Backend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; Start-Frontend"

# Open browser
Start-Process "http://localhost:3000"