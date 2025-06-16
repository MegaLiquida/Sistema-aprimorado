@echo off
echo ========================================
echo    Sistema EAN - Instalador Windows 11
echo ========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado!
    echo Por favor, instale Python 3.8 ou superior de https://python.org
    pause
    exit /b 1
)

echo Python encontrado!
echo.

REM Criar ambiente virtual
echo Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo ERRO: Falha ao criar ambiente virtual
    pause
    exit /b 1
)

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instalar dependências
echo Instalando dependências...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependências
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Instalação concluída com sucesso!
echo ========================================
echo.
echo Para iniciar o sistema, execute: iniciar_sistema.bat
echo.
pause

