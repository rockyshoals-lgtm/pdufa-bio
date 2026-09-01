@echo off
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"
C:\Python314\python.exe -u readout_scan.py --days 90 --step 7 --dates --max-fetch 140 --deep 120 --out readout_forward.csv > "logs\_scan_verify.txt" 2>&1
echo EXITCODE %ERRORLEVEL% >> "logs\_scan_verify.txt"
