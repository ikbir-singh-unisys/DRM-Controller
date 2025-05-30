@echo off
cd /d C:\DrmController

:: Start FastAPI backend
pm2 start start_controller.py --name drm-controller

:: Delay a bit to make sure backend loads
timeout /t 5

:: Start React frontend
pm2 start cmd --name drm-frontend -- /c "serve -s dist -l 5173"

:: Save the PM2 process list
pm2 save

exit