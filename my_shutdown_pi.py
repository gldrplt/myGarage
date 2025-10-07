#!/bin/python
# Simple script for shutting down the raspberry Pi at the press of a button

from gpiozero import Button, Device
import os

from gpiozero.pins.lgpio import LGPIOFactory
# force PinFactory
Device.pin_factory = LGPIOFactory()
print(Device.pin_factory)
# Watch pin GPIO 21 (BOARD 40)
btn = Button(21)

# Wait for button to be pressed
btn.wait_for_press()

# shutdown pi
print("shutting down...")
os.system("sudo shutdown -h now")



