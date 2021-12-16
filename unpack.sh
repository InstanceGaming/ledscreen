#!/usr/bin/env bash
unzip -u -o ledscreen.zip -x **env/** screend/frames/**
dos2unix **/*
rm *.bat
sudo chmod +x **/*.sh
rm ledscreen.zip