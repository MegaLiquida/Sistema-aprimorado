# Verificar Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python não encontrado! Instale de python.org" -ForegroundColor Red
    exit 1
}

Write-Host "🐍 Criando ambiente virtual..." -ForegroundColor Cyan
python -m venv venv

Write-Host "🔧 Ativando ambiente..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

Write-Host "📦 Instalando dependências..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "✅ Instalação concluída!" -ForegroundColor Green
Write-Host "🚀 Para iniciar: .\iniciar-sistema.ps1" -ForegroundColor Yellow
