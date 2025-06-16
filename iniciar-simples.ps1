Write-Host "🚀 Iniciando Sistema EAN..." -ForegroundColor Cyan

# Ativar ambiente virtual
& ".\venv\Scripts\Activate.ps1"

# Verificar se main.py existe
if (-not (Test-Path ".\src\main.py")) {
    Write-Host "❌ main.py não encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host "📍 Sistema será executado em: http://localhost:5000" -ForegroundColor Yellow
Write-Host "👤 Login: admin / admin" -ForegroundColor Green
Write-Host ""

# Abrir navegador após 3 segundos
Start-Job -ScriptBlock {
    Start-Sleep 3
    Start-Process "http://localhost:5000"
} | Out-Null

# Iniciar sistema
python .\src\main.py
