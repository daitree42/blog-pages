@echo off
cd /d C:\cc\blog-pages
C:\Python314\python.exe -u qwen_process.py --input "podcast-site\transcripts_raw\2026-07-28-The_Daily-What_AI_Is_Actually_Doing_to_the_Economy.txt" --show "The Daily" --episode "What A.I. Is Actually Doing to the Economy" --date "2026-07-28" --category "播客" --tags "播客,The Daily,NYT,AI经济" --link "https://www.nytimes.com/the-daily" --build
pause
