@echo off
echo Installing Python dependencies...
pip install -r requirements.txt

echo Starting AI Studio Video Generator...
python video_generator.py

pause
