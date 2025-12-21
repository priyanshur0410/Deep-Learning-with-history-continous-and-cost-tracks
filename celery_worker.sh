#!/bin/bash
# Celery worker startup script for Unix/Linux
celery -A creston worker --loglevel=info

