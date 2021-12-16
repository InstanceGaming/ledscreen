#!/usr/bin/env bash
screen -dmS screend env/bin/python -OO main.py -c screen.toml tcp://127.0.0.1:9998
