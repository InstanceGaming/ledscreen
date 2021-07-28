@echo off
.\env\Scripts\sphinx-apidoc.exe -f -M -o docs\source\ ledscreen ledscreen\ipc_common.py
.\docs\make.bat html