@echo off
cd /d "C:\Users\Bishal\Desktop\Final Project\StockSanket"

call venv\Scripts\activate.bat

if not exist logs (
    mkdir logs
)

python manage.py update_stock_history >> logs\update_%date:~10,4%-%date:~4,2%-%date:~7,2%.log 2>&1

call venv\Scripts\deactivate.bat
