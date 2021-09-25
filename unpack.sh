#!/usr/bin/env bash
unzip -u -aa -o ledscreen.zip -x **env/** screend/frames/**
rm *.bat
sudo chmod +x *.sh
rm ledscreen.zip