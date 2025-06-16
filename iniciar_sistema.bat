@echo off
echo ========================================
echo      Sistema EAN - Iniciando...
echo ========================================
echo.

REM Verificar se ambiente virtual existe
if not exist "venv\Scripts\activate.bat" (
    echo ERRO: Ambiente virtual não encontrado!
    echo Execute primeiro: instalar.bat
    pause
    exit /b 1
)

REM Ativar ambiente virtual
call venv\Scripts\activate.bat

REM Iniciar aplicação
echo Iniciando Sistema EAN...
echo.
echo Acesse o sistema em: http://localhost:5000
echo.
echo Usuario admin: admin / admin
echo.
echo Pressione Ctrl+C para parar o sistema
echo.

python src\main.py

pause

