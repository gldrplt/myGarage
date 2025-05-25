#!/bin/python
# Simple script for shutting down the raspberry Pi at the press of a button

from gpiozero import Button
import os

# Watch pin GPIO 21 (BOARD 40)
btn = Button(21)

# Wait for button to be pressed
btn.wait_for_press()

# shutdown pi
os.system("sudo shutdown -h now")



