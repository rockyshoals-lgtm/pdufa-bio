@echo off
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"
C:\Python314\python.exe -u _conf_exhibit_check.py > "logs\_conf_exh.txt" 2>&1
echo DONE >> "logs\_conf_exh.txt"
