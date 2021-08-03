@echo off

IF EXIST "env\Scripts\python.exe" (
  .\env\Scripts\python.exe app.py %*
) ELSE (
  echo Could not find python.exe
  PAUSE
)