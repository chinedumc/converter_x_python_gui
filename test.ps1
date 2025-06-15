# PowerShell script to run tests

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

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate
}

# Function to run backend tests
function Test-Backend {
    Write-Host "\nRunning backend tests..." -ForegroundColor Green
    Set-Location backend

    # Run pytest with coverage
    python -m pytest tests/ --cov=. --cov-report=term-missing -v

    # Run security checks
    Write-Host "\nRunning security checks..." -ForegroundColor Yellow
    python -m bandit -r . -x tests/

    # Run type checking
    Write-Host "\nRunning type checking..." -ForegroundColor Yellow
    python -m mypy .

    Set-Location ..
}

# Function to run frontend tests
function Test-Frontend {
    Write-Host "\nRunning frontend tests..." -ForegroundColor Green
    Set-Location frontend

    # Run Jest tests
    npm test

    # Run ESLint
    Write-Host "\nRunning ESLint..." -ForegroundColor Yellow
    npm run lint

    # Run TypeScript compilation check
    Write-Host "\nChecking TypeScript compilation..." -ForegroundColor Yellow
    npm run type-check

    Set-Location ..
}

# Main execution
try {
    # Run backend tests
    Test-Backend

    # Run frontend tests
    Test-Frontend

    Write-Host "\nAll tests completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "\nError occurred during testing: $_" -ForegroundColor Red
    exit 1
}