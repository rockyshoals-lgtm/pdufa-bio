@echo off
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"
C:\Python314\python.exe -u readout_scan.py --days 90 --step 7 --dates --max-fetch 140 --deep 120 --out readout_forward.csv > "logs\_ro_scan.txt" 2>&1
C:\Python314\python.exe -u ctgov_readouts.py >> "logs\_ro_scan.txt" 2>&1
C:\Python314\python.exe -u readout_gold_dates.py >> "logs\_ro_scan.txt" 2>&1
echo ALLDONE >> "logs\_ro_scan.txt"
