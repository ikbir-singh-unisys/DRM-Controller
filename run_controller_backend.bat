@echo off

:: Change to your project directory
cd /d C:\DrmController


:: Start the FastAPI worker using PM2 and virtual env's Python
pm2 start start_controller.py --name drm-controller

:: Optionally save the PM2 process list (for automatic resurrection)
pm2 save

:: Exit the batch script
exit
