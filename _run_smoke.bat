@echo off
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
set SEC_USER_AGENT=pdufa.bio research support@pdufa.bio
C:\Python314\python.exe -u readout_scan.py --days 7 --step 7 --dates --max-fetch 5 --deep 12 --out readout_smoke.csv > "Momentum Scanner\_DATA\smoke.txt" 2>&1

