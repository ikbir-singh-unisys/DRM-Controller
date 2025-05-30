@echo off

:: Change to your project directory
cd /d C:\DrmController


:: Start React frontend using 'serve' with PM2
pm2 start cmd --name drm-frontend -- /c "serve -s dist -l 5173"

:: Optionally save the PM2 process list (for automatic resurrection)
pm2 save

:: Exit the batch script
exit
