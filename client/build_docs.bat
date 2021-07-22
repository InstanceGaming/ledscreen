@echo off
.\env\Scripts\sphinx-apidoc.exe -f -e -M -o docs\source\ ledscreen ledscreen\ipc_common.py
.\docs\make.bat html