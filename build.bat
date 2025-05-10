@echo off
echo Installing dependencies...
npm install

echo Building executable...
npm run build

echo Done! You can now run video-generator.exe
pause
