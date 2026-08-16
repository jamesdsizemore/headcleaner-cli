<#
headcleaner installer for Windows PowerShell 5+ / PowerShell Core 7+
Usage:   irm https://...install.ps1 | iex
   or:    .\install.ps1 [-Version X.Y.Z] [-FromSource] [-NoOfficeCli]

ENV VARS:
    HEADCLEANER_VERSION   Override the version to install
#>

[CmdletBinding()]
param(
    [string]$Version = $env:HEADCLEANER_VERSION,
    [switch]$FromSource,
    [switch]$NoOfficeCli,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

# ---- Pretty output ----
function Write-Banner {
    Write-Host "  " -NoNewline
    Write-Host "⚡ headcleaner installer" -ForegroundColor Cyan
    Write-Host "  ──────────────────────────" -ForegroundColor DarkGray
}

function Write-Step   { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Cyan }
function Write-Info   { param($msg) Write-Host "  · $msg" -ForegroundColor DarkGray }
function Write-Warn   { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Magenta }
function Write-Fail   { param($msg) Write-Host "  � $msg" -ForegroundColor Red; exit 1 }

Write-Banner

# ---- Check Python ----
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    Write-Fail "Python not found. Install Python 3.12+ or pass -Python <path>"
}

$pyVersionOutput = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyParts = $pyVersionOutput.Split('.')
$pyMajor = [int]$pyParts[0]
$pyMinor = [int]$pyParts[1]

if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 12)) {
    Write-Fail "Python $pyVersionOutput found; headcleaner needs 3.12+"
}

Write-Step "Python $pyVersionOutput"

# ---- Install uv ----
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Info "installing uv..."
    try {
        irm https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
        $env:PATH = "$env:USERPROFILE\.local\bin;$env:APPDATA\uv\bin;$env:PATH"
    } catch {
        Write-Fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Fail "uv not on PATH after install. Open a new shell and re-run."
}

Write-Step "uv $((uv --version).Split()[1])"

# ---- Install headcleaner ----
if ($FromSource) {
    Write-Info "installing from source..."
    uv tool install .
} else {
    $target = if ([string]::IsNullOrEmpty($Version)) { "headcleaner" } else { "headcleaner==$Version" }
    Write-Info "installing $target..."
    uv tool install $target
}

Write-Step "headcleaner installed"

# ---- Install OfficeCLI ----
if (-not $NoOfficeCli) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Info "installing OfficeCLI engine..."
        try {
            npm install -g @officecli/officecli 2>&1 | Out-Null
            Write-Step "OfficeCLI installed"
        } catch {
            Write-Warn "OfficeCLI install failed — DOCX/XLSX/PPTX files will be skipped"
            Write-Warn "  Re-run with:  npm install -g @officecli/officecli"
        }
    } else {
        Write-Warn "npm not found — OfficeCLI not installed"
        Write-Warn "  Install Node.js from nodejs.org, then:  npm install -g @officecli/officecli"
    }
}

# ---- Verify ----
$hc = Get-Command headcleaner -ErrorAction SilentlyContinue
if ($hc) {
    try {
        $ver = headcleaner --version 2>$null
        Write-Step "headcleaner $ver on PATH"
    } catch {
        Write-Step "headcleaner on PATH"
    }
} else {
    Write-Warn "headcleaner not on PATH yet. Open a new PowerShell window."
}

Write-Host ""
Write-Host "  Installation complete. Try:" -ForegroundColor White
Write-Host "    headcleaner --help"
Write-Host "    headcleaner agents"
Write-Host "    headcleaner convert .\inbox --format both --output .\out"
Write-Host ""
