################################################################
#
# gwFunctions.py
#
#   Functions used by GarageWeb application
#
################################################################
import os
import sys
import time
import pause
from datetime import datetime, timedelta
from subprocess import run
import shutil
import psutil
from gw_Classes import myError, gwColors
from threading import Timer, Event, Thread

#from twilio.rest import Client

def fmtts(time):  # format time stamp for log entry
    z = time
    hms = z.strftime("%H:%M:%S")  # hours:min:sec
    ms = z.strftime(".%f")        # microseconds 6 digits
    ms = ms[0:3]                  # 2 digits
    ts = hms + ms                 # formatted time stamp
    return ts

def get_path():             # get directory where program started from
    cwd = os.getcwd()       # current working directory
    x = str(sys.argv[0])    # full path of program start directory
    i = x.rfind('/')        # test if program started from subdirectory

    if i == -1:             # if not true - rpath = cwd
        rpath = cwd
    else:
        rpath = x[0:i]      # else return full path of program start directory

    return rpath

def build_gwdict(fname, gwdict, gwdictcomment):

    gwdict.clear()
    gwdictcomment.clear()

    with open(fname, "r") as f:
        z = f.read()

    x = z.split('\n')       #break into individual lines
    for a in x:
        b = a.split('#')    #check if comment only line
        if b[0] != '':
            # get comment if any
            c = ''
            if len(b) > 1:
                c = b[1].lstrip()   #remove leading spaces
                c = '\t# ' + c
    # remove comment
            y = b[0]
            y = y.split('#')    #remove comment
            b = y[0]
            y = b.split('=')
            key = y[0].rstrip() #remove trailing spaces from key
            z = y[1].lstrip()   #remove leading spaces from val
            val = y[1].rstrip() #remove trailing spaces from val

            # create dictionary entries
            gwdict[key] = val       #save value for key
            gwdictcomment[key] = c  #save comment for key

def update_ini(fname, gwdict, gwdictcomment):
    f = open(fname,"w")
    a = '#\n'
    f.write(a)
    a = '# parameters used by GarageWeb App' + '\n'
    f.write(a)
    a = '#\n'
    f.write(a)

    mylist = []

    for x in gwdict.items():
        mylist.append(x)
    mylist.sort()

    for x in mylist:
        p1 = x[0]   # parm name
        v1 = x[1]   # parm value
        c1 = gwdictcomment[p1]  # parm comment
        a = p1 +'=' + v1 + c1 + '\n'
        f.write(a)
    f.close

def writelog(fname,msg, color=None):
    if color is not None:
        msg = colorstring(msg, color)    # set text color
    f = open(fname,"a")
    f.write(msg)
    f.close()

def writeoctime(dto):
    msg = dto.strftime("%Y-%m-%d %l:%M:%S %p")
    f = open('gw_octime.txt','w')
    f.write(msg)
    f.close()


def calc_reboot_dto(hhmm: str) -> datetime:
    """Return a datetime for today at hhmm.
    If that time has already passed, return the same time tomorrow."""
    hh = int(hhmm[0:2])
    min = int(hhmm[2:5])
    now = datetime.now()
    target = now.replace(hour=hh, minute=min, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    return target

def reboot_at(hhmm, function, *args, **kwargs):
    """Return a datetime dto for today at hhmm.
    If that time has already passed, return the same time tomorrow."""
    hh = int(hhmm[0:2])
    min = int(hhmm[2:5])
    now = datetime.now()
    target = now.replace(hour=hh, minute=min, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    delay = (target - now).total_seconds()
    if delay < 0:
        print("⚠️ Target time is in the past!")
        return None
    timer = Timer(delay, function, args=args, kwargs=kwargs)
    timer.daemon = True     # mark as daemon to allow program close
                            # before timer finishes
    timer.start()           # start timer
    return timer

def rebootnow(logfile, gwColors):     # reboot system
    
    try:
        #   test if check_throttled command exists
        #   Run check_throttled
        curtime = datetime.now()
        cmd = 'check_throttled'
        if shutil.which(cmd):
            chk = run(cmd)
            rc = chk.returncode
            z = datetime.now()
            ts = fmtts(z)
            if rc == 0:
                msg = curtime.strftime("\n\t    " + ts + "    -- No system throttling since last reboot... \n")
                mcolor = gwColors.bgreen # type: ignore
            else:
                msg = curtime.strftime("\n\t    " + ts + "    -- Warning - system throttling occurred since last reboot... \n")
                mcolor = gwColors.bred # type: ignore
            writelog(logfile,msg, mcolor)
        else:
            msg = "\n--- Error --- check_throttled function not found"
            writelog(logfile,msg, gwColors.bred)             # type: ignore
            p = os.getenv('PATH')
            p = "\nPath = " + p
            writelog(logfile,p)

    #   Reboot system
        time.sleep(60)       # wait 60 seconds
        z = datetime.now()
        ts = fmtts(z)

        msg = curtime.strftime("\n\t    " + ts + "    -- Raspberry Pi Re-Booting... \n\n")
        writelog(logfile,msg, gwColors.byellow) # type: ignore
        print(msg)

        os.system("sudo reboot now")
        return True
    except Exception as error:
        myerr = myError(error, 'waitforreboot')
        return

def trimlog(logdays,logfile):
    try:
        with open(logfile,'r') as f:
            z = f.read()        # get current log file data

        a = z.split('Started')
        i = len(a)
        if i <= logdays:     # check if log file exceeds gwLogDays
            return
    except:
        f = open(logfile,'w')
        f.close()
        return

    newlogname = logfile + '.old'
    os.renames(logfile,newlogname) #rename logfile to gw_log.txt.old

    outlog = ''
    for j in range(i - logdays, i-1):
        b=a[j]              #   b contains first part of log day
        k=b.rindex('\n')
        c=b[k+1:len(b)]     #   c is first part of log day

        e=''
        if j <= i:
            d=a[j+1]        #   d contains second part of log day
            l = d.rindex('\n') + 1
            e = d[0:l]      #   e is second part of log day
        logday = c + 'Started' + e  #   build log day entry
        outlog = outlog + logday  #   add log day to trimlog

    #   write trimmed logfile
    f = open(logfile,'w')
    f.write(outlog)
    f.close()


def get_tgt_pids(tgt):   # return array of pids for tgt
    tgt_pid = ""
    tgt_pids =[]
    vscode = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
        try:
            proccmd = proc.cmdline()
        except:
            pass
        procid = proc.pid
        #        procexe = proc.exe()
        procname = proc.name()

        if len(proccmd) > 0:
            for x in proccmd:
                if tgt in x:
                    #                    print(proc.pid, '\n',proc.name(),'\n', proc.cmdline(),'\n', proexe,'\n')
                    if not "gunicorn: master" in x:
                        tgt_pids.append(str(proc.pid))
#                    print("proccmd = ",proccmd,type(proccmd))
                    else:
                        pass
                    cmdline=str(proccmd)
                    #                    print("cmdline = ",cmdline,type(cmdline))
                    i = cmdline.find('vscode')
                    print("i = ",i)
                    if i > 0:
                        vscode = True
    try:
        print(tgt_pids,"vscode ? ",vscode)
        tgt_pid = tgt_pids[0]   # get first pid
        if vscode:              # if tgt in running under vscode use second pid
            tgt_pid = tgt_pids[1]
    except:
        pass
    return tgt_pids, vscode  # return tgt pid

def sendsignal(tgt, signal):    # send signal to tgt pids
    if isinstance(tgt, str):    # convert string to list
        tgt = tgt.split()

    try:
        for x in tgt:           # loop through list of pids
            print("Sending signal "+signal+" to pid " + x)
            cmd = "kill -" + signal +" " + x
            os.system(cmd)
    except:
        pass

def getlogdays(logfile):
    #   returns array of logfile days
    logdays = []
    i = 0

    with open(logfile,'r') as f:
        z = f.read()        # get current log file data
        a = z.split('Started')
        i = len(a)

    if i <= 1:
        return logdays

    fp = ''                         # fp = first part of day
    for j in range(0, i -1):
        if fp == '':
            fp = a[j]
        b = a[j+1]
        k = b.rindex('\n')
        sp = b[0:k]                 # sp = second part of day
        ld = fp + 'Started' + sp    # rebuild log day
        logdays.append(ld)          # add to array

        fp  = b[(k+1):]             # get first part of next day

    return logdays

def colorstring(text, color):
    #   Split on <new line>
    #   Wrap each segment with <color><segment><reset>
    reset = '\033[0m'      # escape sequence to RESET text
    c = text
    a = text.split('\n')     # split on new line

    if len(a) > 0:
        c = ''               # start output string
        for x in a:
            if len(x) > 0:
                c = c + color + x + reset   # build output string
            else:
                c = c + '\n' # add new line
    return c                 # return colorized string

# def send_sms(gwdict, gwmsg):
#     account_sid = gwdict['sms_sid']
#     auth_token = gwdict['sms_token']

#     client = Client(account_sid, auth_token)

#     sms_from = gwdict['sms_from']
#     sms_to = gwdict['sms_phone1']
#     msg = gwmsg
#     if sms_to != '':
#         client.messages.create(
#             to=sms_to,
#             from_=sms_from,
#             body=msg
#         )

#     sms_to = gwdict['sms_phone2']
#     if sms_to != '':
#         client.messages.create(
#             to=sms_to,
#             from_=sms_from,
#             body=msg
#         )
