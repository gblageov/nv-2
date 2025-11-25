@echo off
setlocal enabledelayedexpansion

:: Проверка дали съществува виртуална среда
if not exist "venv\" (
    echo Създаване на виртуална среда...
    python -m venv venv
    echo Виртуалната среда е създадена.
)

:: Активиране на виртуалната среда
call venv\Scripts\activate

:: Проверка за .env файл
if not exist ".env" (
    echo Създаване на .env файл от шаблона...
    copy ".env.example" ".env"
)

:: Инсталиране на зависимостите
echo Проверка на зависимостите...
pip install -r requirements.txt

:: Стартиране на приложението
echo Стартиране на приложението...
python main.py

:: Пауза, за да може да се видят съобщенията
pause
