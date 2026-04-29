@echo off
title TELia Brain - Servidor de IA Local
color 0A

cd /d "%~dp0"

echo       Iniciando o Cerebro do TELia...

IF EXIST "venv_chatter\Scripts\activate.bat" GOTO ambiente_existe

echo [!] Ambiente virtual nao encontrado ou incompleto.
echo [!] Criando ambiente FORCANDO O PYTHON 3.8...

:: AQUI ESTA A MAGICA: Usando py -3.8 em vez de python
py -3.8 -m venv venv_chatter

echo [!] Ativando ambiente e instalando dependencias...
call "venv_chatter\Scripts\activate.bat"
pip install -r requirements.txt
echo [!] Instalacao concluida!
GOTO iniciar_api

:ambiente_existe
echo [V] Ambiente virtual encontrado e ativo.
call "venv_chatter\Scripts\activate.bat"

:: Adicionamos esta linha para ele sempre checar se tem biblioteca nova!
echo [!] Sincronizando dependencias...
pip install -r requirements.txt --quiet

:iniciar_api

echo.
echo [V] Iniciando a API Flask...
echo [!] Para desligar, feche esta janela ou aperte CTRL+C.
echo.

:: O ambiente ativo ja vai forcar o python certo aqui
python api_ia.py 

pause