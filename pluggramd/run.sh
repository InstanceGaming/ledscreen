#!/usr/bin/env bash
screen -S pluggramd env/bin/python main.py programs tcp://localhost:5555 tcp://localhost:5556
