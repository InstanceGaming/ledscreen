@echo off
python pack.py
scp -i F:\Backups\ledscreen\new_ledscreen ledscreen.zip pi@192.168.0.11:~/ledscreen/