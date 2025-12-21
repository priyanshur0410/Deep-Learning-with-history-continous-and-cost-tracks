@echo off
REM Celery worker startup script for Windows
celery -A creston worker --loglevel=info --pool=solo

