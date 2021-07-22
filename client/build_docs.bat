@echo off
del docs\source\ledscreen.rst
del docs\source\modules.rst
.\env\Scripts\sphinx-apidoc.exe -o docs\source\ ledscreen
.\docs\make.bat html