@echo off
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"
C:\Python314\python.exe -u conference_miner.py --days 60 --step 7 --max-fetch 120 > "logs\_conf_miner.txt" 2>&1
C:\Python314\python.exe -u readout_gold_dates.py >> "logs\_conf_miner.txt" 2>&1
echo ALLDONE >> "logs\_conf_miner.txt"
