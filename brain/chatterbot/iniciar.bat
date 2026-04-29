@echo off
title TELia Brain - Servidor de IA Local
color 0A

echo       Iniciando o chatterbot do TELia...

:: Verifica se a pasta do ambiente virtual existe
IF NOT EXIST "venv_chatter" (
    echo [!] Ambiente virtual nao encontrado.
    echo [!] Criando ambiente (Certifique-se de usar Python 3.8)...
    python -m venv venv_chatter
    
    echo [!] Ativando ambiente e instalando dependencias...
    call venv_chatter\Scripts\activate
    pip install -r requirements.txt
    echo [!] Instalacao concluida!
) ELSE (
    echo [V] Ambiente virtual encontrado.
    call venv_chatter\Scripts\activate
)

echo.
echo [V] Iniciando a API Flask...
echo [!] Para desligar, feche esta janela ou aperte CTRL+C.
echo.

python api_ia.py
pause