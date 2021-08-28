#!/usr/bin/env bash
screen -S screend env/bin/python main.py -c screen.toml tcp://localhost:5555
