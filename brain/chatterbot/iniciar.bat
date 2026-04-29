@echo off
title TELia Brain - Servidor de IA Local
color 0A

echo       Iniciando o Cerebro do TELia...

:: Verifica se a pasta do ambiente virtual já existe
IF EXIST "venv_chatter" GOTO ambiente_existe

echo [!] Ambiente virtual nao encontrado.
echo [!] Criando ambiente (Certifique-se de usar Python 3.8)...
python -m venv venv_chatter

echo [!] Ativando ambiente e instalando dependencias...
call venv_chatter\Scripts\activate
pip install -r requirements.txt
echo [!] Instalacao concluida!
GOTO iniciar_api

:ambiente_existe
echo [V] Ambiente virtual encontrado.
call venv_chatter\Scripts\activate

:iniciar_api
echo.
echo [V] Iniciando a API Flask...
echo [!] Para desligar, feche esta janela ou aperte CTRL+C.
echo.

:: Note que aqui coloquei pi_ia.py para bater com o seu print anterior!
python pi_ia.py 
pause