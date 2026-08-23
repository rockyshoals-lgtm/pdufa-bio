@echo off
REM Deep conference-presenter sweep. EDGAR full-text search is slow, so this runs detached via
REM Start-Process rather than inline (tool calls time out ~25s).
cd /d C:\Users\dcmoo\Documents\Python\9realms
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"
set "PYTHONIOENCODING=utf-8"
C:\Python314\python.exe conference_presenter_miner.py --days 400 > _presenter_mine.log 2>&1
echo DONE >> _presenter_mine.log
