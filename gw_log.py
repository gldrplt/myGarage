#################################################################################
#	gw_log.py
#
#	version using gpiozero
#
#	Monitors garage door position
#
#     Updated to allow gw_web.py to run on gunicorn web server
#     uses websockets to refresh web page when door state changes
#     use UNIX SOCKET to communicate with gw_web.py when door state changes
#
#     Receives signals from gw_web.py app to activate door
#
#       GPIO Pin numbers refer to board connector NOT the Broadcom chip
#       GPIO Pins:       7 Activates Relay(open/close door)
#                       13 Motion Detector Sensor
#                       15 Motion Detected LED
#                       16 Door Closed
#                       18 Door Open
#                       11 Door Closed LED
#                       12 Door Open LED
#
#       Motion Detector wiring
#               From Back, Left to Right
#                       Red, Black,Green + Black to LED
#                       Yellow to LED
#
#       Main unit ==> motion detector
#               Blue   ==> Orange
#               Red    ==> Red
#               Yellow ==> Brown
#               Green  ==> Blue
#
#################################################################################

import os
import sys
import signal
import time
from datetime import datetime
import gw_Functions as gwf
import threading
from threading import Timer, Event, Thread
from watchfiles import watch
import multiprocessing
from gpiozero import Button, LED, PWMLED, Device
from contextlib import contextmanager
from gw_Classes import myError, mySignals, gwColors
import socket
import json

#   context manager to perform gpio cleanup
@contextmanager
def gpio_devices():
    try:
        yield
    finally:
        for dev in devices:     # close each gpio device
            try:
#                print("Closing",dev)
                dev.close()
            except:
                print("Error closing device",dev)

def AbortTerm(signum, frame):
    global endmsg
    print("\rat AbortTerm")
    endmsg = "User sent SIGABRT ..."
    print(signum, signal.strsignal(signum))
    stop_pgm_event.set()

def SystemdTerm(signum, frame):
    global endmsg
    print("\rat SystemdTerm")
    endmsg = "Systemd terminated program sent SIGTERM ..."
    print(signum, signal.strsignal(signum))
    stop_pgm_event.set()

def UserTerm(signum, frame):
    global endmsg
    print("\rat UserTerm")
    endmsg = "User pressed Ctrl-C ..."
    print(signum, signal.strsignal(signum))
    stop_pgm_event.set()

def ErrorTerm():
    stop_pgm_event.set()

def MotionDetected():
    motionevent.set()

def blinkled():
    try:
        while True:
            while motionevent.is_set():
                motionled.blink(.1,.1)
                motiondetectedbtn.wait_for_press()
                motionled.off()
                motionevent.clear()
            motionevent.wait()

    except Exception as error:
        location = "at blinkled"
        myerr = myError(error, location)
        ErrorTerm()

def setparms():
    global gwLogFile
    global gwLogDays
    global gwOpenWarning
    global gwCloseDoor
    global gwOpenTime
    global gwBootTime

    #       Set Log File
    gwLogFile = mypath + '/gwdefaultlog.log' #default log file
    x=gwdict['gwLogFile']
    if x != '' : gwLogFile = mypath + '/' + x   #log file from gw_parms.ini

    #       Get Log File Days count
    gwLogDays = int(gwdict['gwLogDays'])

    #       Set Open Warning Flag
    gwOpenWarning = False
    x = gwdict['gwOpenWarning']
    if x == 'True' : gwOpenWarning = True

    #       Set Close Door Flag
    gwCloseDoor = False
    x = gwdict['gwCloseDoor']
    if x == 'True' : gwCloseDoor = True

    #       Set Open Door Time Limit
    gwOpenTime = 15                 #Default open time in minutes
    x = gwdict['gwOpenTime']
    if x !='' : gwOpenTime = int(x) * 60 # convert to seconds

    #       Set Re Boot Time
    gwBootTime = '2359'             # Set what time to perform reboot
    a = gwdict['gwBootTime']
    if a != '':gwBootTime = a


def watchparmfile(parmfile, gwdict, gwdictcomment):
    # watch for changes to parmfile
    global OldBootTime
    global reboot_timer
    try:
        for changes in watch(parmfile):
            z = datetime.now()  # get time
            ts = gwf.fmtts(z)  # format time stamp
            msg = "\t    " + ts + " -- gw_parms.ini file Changed ...\n"
            gwf.writelog(gwLogFile, msg)
            print(msg)
            gwf.build_gwdict(parmfile, gwdict,
                             gwdictcomment)  # rebuild dictionary
            setparms()  # set parms
            if gwBootTime != OldBootTime:  # if boot time changed relaunch reboot subprocess
                OldBootTime = gwBootTime  # save new boot time
                reboot_timer.cancel()  # cancel old timer
                boot_dto = gwf.calc_reboot_dto(
                    gwBootTime)  # calculate Reboot time and return dto object
                write_reboot_time_log(boot_dto,
                                      gwLogFile)  # write reboot time log msg
                reboot_timer = gwf.reboot_at(gwBootTime,
                                             gwf.rebootnow,
                                             gwLogFile,
                                             gwColors)
    except Exception as error:
        location = "at watchparmfile"
        myerr = myError(error, location)
        ErrorTerm()

def waitforgw_web():
    # wait for gw_web.py
    # send doorstate and octime
    while True:
        gw_web_event.wait()
        print("\nat gw_web started")
        SendDoorState(doorstate, octime_dto)
        gw_web_event.clear()

def SendDoorState(doorstate, dto):       # send doorstate and octime to gw_web.py

    print("at Sending Door State to gw_web")
    octime = dto.strftime("%Y-%m-%d %l:%M:%S %p") # 12hr w/am-pm

    if gw_web_pid:                      # if gw_web.py running, send doorstate
        data = {
              "doorstate" : doorstate,
              "octime" : octime
        }
        msg = json.dumps(data).encode()
        socket_path = "/tmp/gw_socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(socket_path)
            s.sendall(msg)
            print(octime,'Sent Doorstate = ' + doorstate + '\n')

def DoorOpen():
    global doorstate

    openled.on()
    closedled.off()

    octime_dto = datetime.now()
    ts = gwf.fmtts(octime_dto)                 # format time stamp 24hr
    msg = "\t    " + ts + " -- Door is Open \n\n"
    gwf.writelog(gwLogFile,msg)
    print(msg)

    doorstate = "Open"
    SendDoorState(doorstate, octime_dto)

    # Start Door Open Timer
    try:
        if gwOpenWarning or gwCloseDoor:
            timer.start()
    except Exception as error:
        location = "at DoorOpen"
        myerr = myError(error, location)
        ErrorTerm()

def DoorOpening():
    global doorstate

    openled.blink(.1,.1)
    closedled.blink(.1,.1)

    octime_dto = datetime.now()
    ts = gwf.fmtts(octime_dto)                 # format time stamp 24hr
    msg = "\t    " + ts + " -- Door is Opening \n"
    gwf.writelog(gwLogFile,msg)
    print(msg)

    doorstate = "Opening"
    SendDoorState(doorstate, octime_dto)

def DoorClosed():
    global doorstate

    closedled.on()
    openled.off()

    octime_dto = datetime.now()
    ts = gwf.fmtts(octime_dto)                 # format time stamp
    msg = "\t    " + ts + " -- Door is Closed \n\n"
    gwf.writelog(gwLogFile,msg)
    print(msg)
    gwf.writeoctime(z)   # write open/close time for gw_web
    doorstate = "Closed"

    SendDoorState(doorstate, octime_dto)

def DoorClosing():
    global doorstate

    openled.blink(.1,.1)
    closedled.blink(.1,.1)

    octime_dto = datetime.now()            # get time
    ts = gwf.fmtts(octime_dto)                 # format time stamp
    msg = "\t    " + ts + " -- Door is Closing \n"
    gwf.writelog(gwLogFile,msg)
    print(msg)
    doorstate = "Closing"

    SendDoorState(doorstate, octime_dto)

def OpenWarning():   # Door has been open longer than gwOpenTime

    if gwOpenWarning: # Log open warning msg
        z = datetime.now()
        ts = gwf.fmtts(z)                 # format time stamp
        m1 = "\t    " + ts + " -- Garage Door has been open for "
        m2 = gwdict['gwOpenTime'] + " minutes\n"
        msg =  m1 + m2
        gwf.writelog(gwLogFile,msg)
        print(msg)

    if gwdict['smsMsg'] == 'True':   # Send SMS message
        msg = '-\nmyGarage Application\n\nYour garage door has been open for more than:\n'
        msg = msg + gwdict['gwOpenTime'] + ' minutes\n\n'
        if gwCloseDoor:   # add closing door msg to SMS msg
            msg = msg + 'myGarage is closing door\n\n'
            urlmsg = ''
            if gwdict['sms_url1'] != '' :
                urlmsg = urlmsg + "Local URL : " + gwdict['sms_url1'] +'\n\n\n'
            if gwdict['sms_url2'] != '' :
                urlmsg = urlmsg + "Remote URL : " + gwdict['sms_url2'] + '\n'
            msg = msg + urlmsg

        gwf.send_sms(gwdict, msg)  # send SMS message

    if gwCloseDoor:    # close door
        z = datetime.now()
        ts = gwf.fmtts(z)                 # format time stamp
        msg = "\t    " + ts + " -- Garage Door is closing... \n"
        gwf.writelog(gwLogFile,msg)
        print(msg)

        pressdoorbtn.off()
        time.sleep(1)
        pressdoorbtn.on()

def WebGoodPin(signum, frame):     # gw_web.py issued activate door command
    z = datetime.now()
    ts = gwf.fmtts(z)                 # format time stamp
    if doorstate == "Open":
        msg = "\t    " + ts + " -- Garage Door Closed by gw_web.py app... \n"
    else:
        msg = "\t    " + ts + " -- Garage Door Opened by gw_web app.py... \n"

    gwf.writelog(gwLogFile,msg)
    print(msg)

    pressdoorbtn.off()         # press remote
    time.sleep(1)
    pressdoorbtn.on()

def WebBadPin(signum, frame):       # gw_web.py received bad PIN
    z = datetime.now()
    ts = gwf.fmtts(z)                 # format time stamp
    msg = "\t    " + ts + " -- Bad Pin entered to gw_web app... \n"
    gwf.writelog(gwLogFile,msg)
    print(msg)

def write_reboot_time_log(boot_dto,fname):
    curtime = datetime.now()
    ts = gwf.fmtts(curtime)
    #        msg = curtime.strftime("\t    %H:%M:%S    -- Reboot time set to ... ")
    msg = "\t    " + ts + " -- Reboot time set to ... "
    t = datetime.strftime(boot_dto,'%Y %b %d %H:%M:%S')
    msg = msg + t + "\n"
    gwf.writelog(fname, msg, gwColors.byellow)
    print(msg)

def gw_web_started(signum, frame):  # gw_web.py has started - get PID
    global gw_web_pid

    pids = []
    tgt = "gw_web"
    pids, vscode = gwf.get_tgt_pids(tgt)
    gw_web_pid = pids
    print("gw_web.py started ...")
    print("gw_web.py PIDs =",pids)
    gw_web_event.set()            # set gw_web_event
    return

########################################################################
#
#  Start of Program
#
########################################################################
#   if running under systemd, redirect stdout, stderr to file
if os.getenv('running_under_systemd') == 'true':
    sys.stdout = open('gw_web.stdout', 'w')
    sys.stderr = open('gw_web.stderr', 'w')

#     get signals constants
# mysignals = mySignals()

#   initialize gw_web_pid
gw_web_pid = ""

#     Set signal handler for SIGTINT
#     User pressed Ctrl-C
signal.signal(signal.SIGINT, UserTerm)

#     Set signal handler for SIGTERM
#     signal sent by systemd to terminate
signal.signal(signal.SIGTERM, SystemdTerm)

#     set signal handler for SIGUSR1 (10)
#     gw_web app wants to close door
signal.signal(signal.SIGUSR1, WebGoodPin)

#     set signal handler for SIGUSR2 (12)
#     gw_web app was sent Bad PIN code
signal.signal(signal.SIGUSR2, WebBadPin)

#     set signal handler for SIGABRT (6)
#     signal for testing purposes
signal.signal(signal.SIGABRT, AbortTerm)

#     set signal handler for signal (60)
#     signal for gw_web.py has started
signal.signal(60, gw_web_started)

#     get color constants
gwColors = gwColors()

#     TCP/IP Socket parms
gwhost = '127.0.0.1'
gwlogport = 65432

#     make paths relative to program directory
mypath = gwf.get_path()
parmfile = mypath + '/gw_parms.ini'
z = os.stat(parmfile)           # get statistics on ini file
ini_mtime = z.st_mtime          # save last modified time
print('mypath = '+mypath)
print ('\nWorking Directory = '+os.getcwd())
os.chdir(mypath)
print ('Changed to ..')
print ('Working Directory = '+os.getcwd())
envpath = os.environ['PATH']
msg = '\n$PATH = ' + envpath
print(msg)

pid = os.getpid()
print('\ngw_log.py PID = ',pid,'\n')

#        Build Dictionary of parameters and comments
gwdict = {}             # paramater values dictionary
gwdictcomment = {}      # paramater comment dictionary
gwf.build_gwdict(parmfile, gwdict, gwdictcomment)

#       Set parameters from gwdict{}
setparms()

#        Send program starting to logfile
z = datetime.now()
ts = gwf.fmtts(z)                 # format time stamp
msg = z.strftime("%Y %b %d ") + ts + " -- Garage Web Log Program Started ----\n"
gwf.writelog(gwLogFile, msg, gwColors.bwhite)
print(msg)

#     create stop_pgm_event
stop_pgm_event=Event()
stop_pgm_event.clear()

#       Initialize re-boot process
boot_dto = gwf.calc_reboot_dto(gwBootTime)  # calculate Reboot time and return dto object
write_reboot_time_log(boot_dto,gwLogFile)   # write reboot time log msg
OldBootTime = gwBootTime
#     start reboot timer
reboot_timer = gwf.reboot_at(gwBootTime,
                              gwf.rebootnow,
                              gwLogFile,
                              gwColors)

#       Initialize watch parmfile thread
watchthread = Thread(target = watchparmfile, args =\
                     (parmfile, gwdict, gwdictcomment))
watchthread.daemon = True
watchthread.start()

#       Initialize blinkled thread
motionevent = Event()
blinkledthread = Thread(target = blinkled)
blinkledthread.daemon = True
blinkledthread.start()

#       Check # of days to keep in Log File
#       Trim Log File if necessary
gwf.trimlog(gwLogDays,gwLogFile)

#   Use context manager to properly clean up GPIO pins
with gpio_devices():
    #     initialize relay to close door
    pressdoorbtn = LED('BOARD7', active_high=True, initial_value=True)

    #     initialize motion detected switch
    motiondetectedbtn = Button('BOARD13')
    motiondetectedbtn.when_released = MotionDetected

    #     initialize motion led
    brightness = float(gwdict['pwm_duty'])
    motionled = PWMLED('BOARD15', active_high=True, initial_value=brightness)
    motionled.off()

    #     Initialize open and closed switches(buttons)
    opensw = Button('BOARD18', pull_up=True, active_state=None, bounce_time=.5, hold_time=.25)
    opensw.when_pressed = DoorOpen
    opensw.when_released = DoorClosing
    openled = LED('BOARD12')

    closedsw = Button('BOARD16', pull_up=True, active_state=None, bounce_time=.5, hold_time=.25)
    closedsw.when_pressed = DoorClosed
    closedsw.when_released = DoorOpening
    closedled = LED('BOARD11')

    #        Create list of gpio devices
    devices = [
        pressdoorbtn,
        motiondetectedbtn,
        motionled,
        opensw,
        openled,
        closedsw,
        closedled
    ]

    #        Initialize door open timer
    if gwOpenWarning or gwCloseDoor:
        timer = Timer(gwOpenTime, OpenWarning)

    #        Determine initial status of door
    doorstate = 'Unknown'
    laststate = ''
    if closedsw.is_pressed:
        doorstate = 'Closed'
        laststate = 'Door is Closed'
        closedled.on()

    if opensw.is_pressed:
        doorstate = 'Open'
        laststate = 'Door is Open'
        openled.on()

    if laststate == '':
        laststate = 'Door State is Unknown'
        closedled.blink(.1,.1)
        openled.blink(.1,.1)

    octime_dto = datetime.now()
    ts = gwf.fmtts(octime_dto)                 # format time stamp 24hr
    msg = "\t    " + ts + " -- " + laststate + "\n\n"
    gwf.writelog(gwLogFile,msg)
    print(msg)

    #       Initialize wait for gw_web.py thread
    gw_web_event = Event()
    waitforgw_webthread = Thread(target = waitforgw_web)
    waitforgw_webthread.daemon = True
    waitforgw_webthread.start()

    #        Blocking Wait for event
    try:
        print("gw_log.py waiting for change in door status :\n")
        stop_pgm_event.wait()
    except Exception as error:
        location = "Main Program (gw_log.py)at Blocking Wait ..."
        myerr = myError(error, location)
        ErrorTerm()

#     Exit program

z = datetime.now()
ts = gwf.fmtts(z)                 # format time stamp
msg = ""
try:
    if myerr:         # if error occurred
        msg = "\n\t    " + ts + " -- " + myerr.errname + \
              " at " + myerr.location + " " + myerr.errtype + "\n"
except:
    pass

msg = "\n\t    " + ts + " -- " + endmsg + "\n" + \
      msg + \
      "\n\t    " + ts + " -- Garage Web Log Program Shutdown ---\n\n"
gwf.writelog(gwLogFile,msg, gwColors.byellow)
print('\r'+msg)

#   Cancel reboot_timer to speed up program shutdown
reboot_timer.cancel()

#########################################################
#
#        End of gw_log.py
#
#########################################################
