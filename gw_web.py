############################################################################
#       gw_web.py
#
#       ver 6.0
#
#       No longer using gpiozero or RPi.GPIO
#
#       uses FastAPI to allow websockets on ASGI web server
#       
#       uses websockets to refresh web page when door state changes
#
#       Use Unix Socket to listen to gw_log.py to 
#       indicate change in door state
#
#       Send SIGUSR1 signal to gw_log.py to activate door
#       Send SIGUSR2 signal to gw_web.py if Bad Pin
#            
############################################################################
import os
import sys
from datetime import datetime
import gw_Functions as gwf
import psutil
from threading import Event
from threading import Thread
from gw_Classes import mySignals,  ConnectionManager
import re
import socket
#   FastAPI imports
from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates  
from typing import List
import asyncio
import uvicorn
import json

def Set_Door_State(state, loop):
    global color, doorstate
    print(f"at Set_Door_State - {state}")
    doorstate = state
    color = {'Closed': 'green', 'Closing': 'orange', 'Open': 'red', 'Opening': 'orange'}.get(state, 'orange')
    loop.call_soon_threadsafe(asyncio.create_task, Send_Door_Change())

async def Send_Door_Change():
    global octime
    global garstatus, garimg, garcolor
    print()
    print(datetime.now())
    print("at Send_Door_Changed ...")
    print("Clients = ",len(manager.active_connections))
    for c in manager.active_connections:
         print(c)
    print()
    
    # reset octime
    octime = datetime.now()
    fmttime = octime.strftime("%l:%M:%S %P")

    # timecmd = 'time=' + fmttime
    # doorcmd = 'door=' + doorstate

    # await manager.broadcast(timecmd)
    # await manager.broadcast(doorcmd)

    garimg = garage_images.get(doorstate, '/static/images/GarageQuestion.gif')
    garcolor = garage_colors.get(doorstate, 'orange')
    garstatus = garage_statuses.get(doorstate, 'status unknown')
    if doorstate in 'OpenClosed': garstatus = garstatus + ' ' + fmttime
    if not pinstatus:
         garstatus = "Invalid PIN"
    mydict = dict( type = 'door',\
                state = doorstate,
                status = garstatus,\
                image = garimg,\
                color = garcolor)
    data = json.dumps(mydict)
    await manager.broadcast(data)

def shutdown():                 # shutdown raspberry pi
    print("at shutdown")
    os.system(homedir + "/bin/myclock -k")
    os.system("sudo shutdown now")

def reboot():                   # reboot raspberry pi
    print("at reboot")
    os.system(homedir + "/bin/myclock -k")
    os.system("sudo shutdown -r now")

def close():                    # shutdown gw_web.py program
    print("\n... Closing webserver ...\n") 
    os.system(homedir + "/bin/myclock -k")
    os.system(homedir + "/bin/killpids gw_web.py")

def chkprog(pname):
     for proc in psutil.process_iter( [ 'cmdline' ]):
          for str in proc.cmdline():    # loog through cmdline()
               if pname in str:
                    return True
     return False

def listen_to_gw_log(loop):
    global doorstate
    print("listen_to_gw_log starting ...")

    # use UNIX Sockets to be notified of change in door status
    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
    sockpath = "/tmp/gw_socket"
    if os.path.exists(sockpath):
        os.remove(sockpath)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.bind(sockpath) 
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                print('Socket created at' + sockpath + '\n' )
                while True:
                    x = conn.recv(1024)
                    if not x:
                        break
                    doorstate = x.decode()
                    print('Door State Changed to: ' + doorstate)
                    if doorstate in ["Closed", "Closing", "Open", "Opening"]:
                        Set_Door_State(doorstate, loop)
                    else:
                        print('Door state unknown')

    print('gw_web ending ...\n')

async def process_web_page_cmd(data):
        global pinstatus
        global garstatus
        try:
            cmdArray = data.split("=")
            cmdType = cmdArray[0]
            cmd = cmdArray[1]
        except:
            print("Illegal cmd sent...")
            return

        if cmdType == "GarageStatus":
             print(manager.active_connections)

        if cmdType == "Admin":
            print("... received data from webadmin page ...")
            print(cmd,'\n')
            if cmd == 'reboot':
                reboot()
            if cmd == 'shutdown':
                shutdown()
            if cmd == 'close':
                close() 

        if cmdType == 'GarCode':
            pin = cmd
            print("PIN = " + pin)
            if pin == gwdict['gwCode']:  # Code if Password is correct
                garstatus = ''
                pinstatus = True
                print("Sending SIGUSR1 (10) to gw_log.py "+gw_log_pid)
                gwf.sendsignal(gw_log_pid, "10") 
            elif pin != "":          # Code if Password is incorrect
                pinstatus = False         # invalid PIN   
                print("Sending SIGUSR1 (12) to gw_log.py "+gw_log_pid)           
                gwf.sendsignal(gw_log_pid, "12")
                print("Invalid PIN ...",pin)

                mydict = dict(type = 'pin')
                data = json.dumps(mydict)
                await manager.broadcast(data)
        
        if cmdType == 'Log':
            print('at get log data for: ',data)

            logfname = gwdict['gwLogFile']
            ans = gwf.getlogdays(logfname)
            cnt = len(ans)
            logdata = ans[cnt - 1 + int(cmd)]
            # remove color escape sequences
            # Regex to match ANSI escape sequences
            # my pattern \x1b\[[0-9;]*m
            pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            logdata = re.sub(pattern,'', logdata)  # Remove escape sequences
            
            z = datetime.now()
            loghdr ='Log File as of ' + z.strftime("%Y %b %d %H:%M:%S")
            logday = cmd 
            logdaycnt = str(cnt) 

            mydict = dict(type = 'LogData', logday = logday, logdays = str(cnt), \
                          logdaycnt = logdaycnt, \
                          loghdr = loghdr, logdata = logdata)
            data = json.dumps(mydict)
            print(data)
            await manager.broadcast(data)

######################################################
#
#   Program Start
#
########################################################

#   if running under systemd, redirect stdout, stderr to file
if os.getenv('Running_Under_Systemd') == 'true':
    sys.stdout = open('gw_web.stdout', 'w')
    sys.stderr = open('gw_web.stderr', 'w')

print('Parmstring = ',sys.argv)
print()
print('PYTHONUNBUFFERED = ',os.getenv('PYTHONUNBUFFERED'))

originalstdout = sys.stdout 
originalstderr = sys.stderr

#   if running in test mode
t_flag = False              # test flag
try:
     if sys.argv[1] == '-t': t_flag = True
except:
     pass

if t_flag == False:     # if running in test mode don't check for gw_log.py
    #   Get PID of gw_log.py
    gw_log_pids, vscode = gwf.get_tgt_pids("gw_log.py")
    if len(gw_log_pids) == 0:
        print('Error - gw_log.py is not running...')
        print('gw_web exiting ...')
        exit()
    else:
        if vscode:
             gw_log_pid = gw_log_pids[1]
        else:
             gw_log_pid = gw_log_pids[0] 
    print("gw_log pid = "+gw_log_pid)
    #   send signal to gw_log.py that gw_web has started
    gwf.sendsignal(gw_log_pid, "60")

#   get signals constants
mysignal = mySignals()

now = datetime.now()
msg = now.strftime("\n%H:%M:%S gw_web.py starting ...\n")
print(msg)

mypath = os.getcwd()
parmfile = mypath + '/' + 'gw_parms.ini'

print ('Working Directory = '+os.getcwd())
os.chdir(mypath)
print ('Changed to ..')
print ('Working Directory = '+os.getcwd())

pid = os.getpid()
print('\ngw_web.py PID = ',pid,'\n')

#   get hostname
hostname = os.uname().nodename
print('Hostname = ',hostname, '\n')

#   get home directory
homedir = os.getenv("HOME")
print('Home Directory = ',homedir,'\n')
      
#   Create FastAPI and WebSocket instances
app = FastAPI()                 
manager = ConnectionManager()

#   serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

#   Jinja2 templates
templates = Jinja2Templates(directory="templates")

#   Build dictionary of parms
gwdict={}	        		        #empty dictionary
gwdictcomment={}
gwf.build_gwdict(parmfile,gwdict,gwdictcomment)	#build dictionary

#   Initialize flags and variables
garimg = ''
garcolor = ''
doorstate = 'unknown'
pinstatus = None        # Flag to show status of PIN code
invertlog = False       # sort direction for log file display 
octime = datetime.now() # set initial value of open/close time
milflag = False         # initialize milflag
dateflag = False        # initialize dateflag
global_logday = 0       # initialize global_logday

#   set garage dictionaries
garage_colors = { \
        'Open' : 'red', \
        'Closed': 'green', \
        'Opening': 'orange', \
        'Closing': 'orange'
        }

garage_statuses = { \
        'Open' : 'is Open since', \
        'Closed': 'is Closed since', \
        'Opening': 'is Opening', \
        'Closing': 'is Closing'
        }
garage_images = { \
        'Open' : '/static/images/GarageRed.gif', \
        'Closed': '/static/images/GarageGreen.gif', \
        'Opening': '/static/images/GarageQuestion.gif', \
        'Closing': '/static/images/GarageQuestion.gif'
        }

#   Determine door status
with open('gw_door_state', 'r') as f:
    doorstate = f.read()
    print("Garage Door State is ",doorstate)

#   Get last open/close time
octime = datetime(9999,1,1,0,0,0,0)   # default dto
with open('gw_octime.txt', "r") as f:
     x = f.read()
     x = x.rstrip()    # remove new line
     octime = datetime.strptime(x, '%Y-%m-%d %I:%M:%S %p')

#   use UNIX sockets to listen to gw_log.py
mainloop = asyncio.get_event_loop()
listenthread = Thread(target = listen_to_gw_log, args=(mainloop,))
listenthread.daemon = True
listenthread.start()

####################################################
#
#   Flask Routes for web server
#
####################################################
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
#        return templates.TemplateResponse("GarageStatus.html",{"request": request})

#       render Garage Status Form based on garage door position        
        print("at Route / ")
        # global garstatus
        # global doorstate
        # global garcolor
        global invertlog

#       flush stdout, stderr buffers
        sys.stdout.flush()
        sys.stderr.flush()

#       reset invertlog flag
        invertlog = False

        garimg = garage_images.get(doorstate, '/static/images/GarageQuestion.gif')
        garcolor = garage_colors.get(doorstate, 'orange')
        garstatus = garage_statuses.get(doorstate, 'status unknown')

#       Get status of garage door and set status message
#       if invalid PIN entered set garstatus
        if doorstate == "Open":
            garstatus = "is Open since " + octime.strftime("%l:%M:%S %P")
            if pinstatus == False:
                garstatus = "Invalid PIN ..."

        elif doorstate == "Closed":
            garstatus = "is Open since " + octime.strftime("%l:%M:%S %P")
            if pinstatus == False:
                garstatus = "Invalid PIN ..."

        return templates.TemplateResponse('GarageStatus.html',\
                                          {"request": request,\
                                           "garname": gwdict['gwGarageName'],\
                                           "gar": doorstate,\
                                           "garstatus": garstatus,\
                                           "garimg": garimg,\
                                           "garcolor": garcolor,\
                                           "hostname": hostname\
                                           })
                        
@app.websocket('/get_web_cmd')
async def get_web_cmd(websocket: WebSocket):
     await manager.connect(websocket)
     try:
          while True:
               data = await websocket.receive_text()
               await process_web_page_cmd(data)
     except WebSocketDisconnect:
        manager.disconnect(websocket)

#       MyClock routes
@app.get("/MyClock/{option}", response_class=HTMLResponse)
async def MyClock(request: Request, option: str = "Admin"):
      print(f"at MyClock/{option} ...")
      global milflag
      global dateflag
      if option == 'Admin':
           pass
      elif option == 'Show':
           os.system(homedir + "/bin/myclock +s")
      elif option == 'Blank':
           os.system(homedir + "/bin/myclock -s")
      elif option == 'ToggleMil':
           if milflag:
               milflag = False
               p = "-m"
           else:
               milflag = True
               p = "+m"
           cmd = homedir + "/bin/myclock "+p
           print(cmd)
           os.system(cmd)
      elif option == 'ToggleDate':
           if dateflag:
               dateflag = False
               p = "-d"
           else:
               dateflag = True
               p = "+d"
           cmd = homedir + "/bin/myclock "+p
           print(cmd)
           os.system(cmd)
      elif option == 'Mil':
           os.system(homedir + "/bin/myclock +m")
      elif option == 'notMil':
           os.system(homedir + "/bin/myclock -m")
      elif option == 'Dim':
           os.system(homedir + "/bin/myclock -b 0")
      elif option == 'Bright':
           os.system(homedir + "/bin/myclock -b 1")
      elif option == 'Segments':
           os.system(homedir + "/bin/myclock -f")
      elif option == 'RestartClock':
           os.system(homedir + "/bin/restartclock")

#      return RedirectResponse(url='/MyClock/Admin')

      return templates.TemplateResponse('mygarageclock.html', {"request": request})

        
@app.get('/Admin', response_class=HTMLResponse)
def Admin(request: Request):
    print("at Admin")
    return templates.TemplateResponse('webadmin.html', {'request': request})

#       end of MyClock routes

@app.get('/Log', response_class=HTMLResponse)
def logfile(request: Request):
        global invertlog
        global logday

        print('at Route /Log')
        logfname = gwdict['gwLogFile']
        ans = gwf.getlogdays(logfname)
        cnt = len(ans)
        logdata = ans[cnt - 1 + int(global_logday)]

        # remove color escape sequences
        # Regex to match ANSI escape sequences
        # my pattern \x1b\[[0-9;]*m
        pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        logdata = re.sub(pattern,'', logdata)  # Remove escape sequences
        
        z = datetime.now()
        logdate = z.strftime("%Y %b %d %H:%M:%S")

        # return render_template('ShowLog.html', fmtdate=logdate, fmtdata=logdata,\
        #                         fmtlday=lday, fmtnumdays=cnt)
        return templates.TemplateResponse("ShowLog.html", \
                                          {"request": request,\
                                           "fmtdate": logdate,\
                                           "fmtdata": logdata,\
                                           "fmtlday": global_logday,\
                                           "fmtnumdays": cnt\
                                           })

@app.get('/ShowParmForm', response_class=HTMLResponse)
async def ShowParmForm(request: Request):
        print("at /ShowParmForm")    
        a = gwdict['gwGarageName']
        b = gwdict['gwCode']
        c = gwdict['gwOpenWarning']
        d = gwdict['gwCloseDoor']
        e = gwdict['gwOpenTime']
        f = gwdict['smsMsg']
        g = gwdict['gwBootTime']
        h = gwdict['gwLogDays']
        i = gwdict['sms_phone1']
        j = gwdict['sms_phone2']
        k = gwdict['sms_url1']
        l = gwdict['sms_url2']
        m = gwdict['pwm_duty']
        
        return templates.TemplateResponse('parmform.html', \
                                          {"request": request,\
                                           "p_gname" : a, \
                                           "p_code" : b, \
                                            "p_openwarn" : c, \
                                            "p_closedoor" : d, \
                                            "p_opentime" : e, \
                                            "p_sendsms" : f, \
                                            "p_boottime" : g, \
                                            "p_logdays" : h, \
                                            "p_phone1" : i, \
                                            "p_phone2" : j, \
                                            "p_url1" : k, \
                                            "p_url2" : l, \
                                            "p_led" : m, \
                                          })

@app.post('/ProcParmForm')
async def ProcParmForm(frm_gname: str = Form(...),\
                       frm_code: str = Form(...), \
                       frm_warn: str = Form(...),\
                       frm_close: str = Form(...),\
                       frm_opentime: str = Form(...),\
                       frm_sendsms: str = Form(...),\
                       frm_boottime: str = Form(...),\
                       frm_logdays: str = Form(...),\
                       frm_phone1: str = Form(...),\
                       frm_phone2: str = Form(...),\
                       frm_url1: str = Form(...),\
                       frm_url2: str = Form(...),\
                       frm_led: str = Form(...) \
                       ):
        global gwdict

        gwdict['gwGarageName'] = frm_gname
        gwdict['gwGarageName'] = frm_gname
        gwdict['gwCode'] = frm_code
        gwdict['gwOpenWarning'] = frm_warn
        gwdict['gwCloseDoor'] = frm_close
        gwdict['gwOpenTime'] = frm_opentime
        gwdict['smsMsg'] = frm_sendsms
        gwdict['gwBootTime'] = frm_boottime
        gwdict['gwLogDays'] = frm_logdays
        gwdict['sms_phone1'] = frm_phone1
        gwdict['sms_phone2'] = frm_phone2
        gwdict['sms_url1'] = frm_url1
        gwdict['sms_url2'] = frm_url2
        gwdict['pwm_duty'] = frm_led
        
        gwf.update_ini(parmfile, gwdict, gwdictcomment)
        
        return RedirectResponse(url="/", status_code=303)

@app.post('/NoProcParmForm')
def NoProcParmForm():
     return RedirectResponse(url="/", status_code=303)

##########################################################
#
#   Launch FastAPI ASGI Web Server
#
##########################################################
#   flush stdout, stderr buffers
sys.stdout.flush()
sys.stderr.flush()
now = datetime.now()
msg = now.strftime("\n%H:%M:%S gw_web.py at Launch FastAPI ASGI server ...\n")
print(msg)

if __name__ == '__main__':
        uvicorn.run(app, host='0.0.0.0', port=int(gwdict['gwPort']))

now = datetime.now()
msg = now.strftime("\n%H:%M:%S gw_web.py ended ...\n")
print(msg)
