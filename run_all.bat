@echo off
cd /d "C:\Users\AMANAH\Documents\Bot zabbix"
start cmd /k node wa_server.js
timeout /t 10
python Mon_Zabbix.py