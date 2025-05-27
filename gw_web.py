############################################################################
#       gw_web.py
#
#       ver 5.0
#
#       No longer using gpiozero or RPi.GPIO
#
#       Monitors gw_door_state file to update door status
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
from flask import Flask, render_template, request, redirect, url_for
from flask_sock import Sock
import gw_Functions as gwf
import psutil
from threading import Event
from threading import Thread
from gw_Classes import mySignals
import re
import socket

def DoorClosed():
     global color, doorstate
     print('at DoorClosed')
     color = 'green'
     doorstate = 'Closed'
     Send_Door_Change()

def DoorClosing():
     global color, doorstate
     print('at DoorClosing')
     color = 'orange'
     doorstate = 'Closing'
     Send_Door_Change()

def DoorOpen():
     global color, doorstate
     print('at DoorOpen')
     color = 'red'
     doorstate = 'Open'
     Send_Door_Change()

def DoorOpening():
     global color, doorstate  
     print('at DoorOpening')   
     color = 'orange'
     doorstate = 'Opening'
     Send_Door_Change()

def Send_Door_Change():
    global octime
    print()
    print(datetime.now())
    print("at Send_Door_Changed ...")
    print("Clients = ",len(client_list))
    for c in client_list:
         print(c)
    print()
    
    # reset octime
    octime = datetime.now()
    fmttime = octime.strftime("%l:%M:%S %P")

    timecmd = 'time=' + fmttime
    doorcmd = 'door=' + doorstate
    cl = client_list.copy()
    for client in cl:
        try:
            print('sending ' + timecmd)
            client.send(timecmd)     # send new octime
            print('sending ' + doorcmd + '\n')
            client.send(doorcmd)     # send color
        except:
            print('\n  no web socket\n  ', client)
            client_list.remove(client)

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

def listen_to_gw_log():
    global doorstate

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
                    if doorstate == "Closed":
                        DoorClosed()
                    elif doorstate == "Closing":
                        DoorClosing()
                    elif doorstate == "Open":
                        DoorOpen()
                    elif doorstate == "Opening":
                        DoorOpening()
                    else:
                        print('Door state unknown') 
    print('gw_web ending ...\n')
######################################################
#
#   Program Start
#
########################################################
t_flag = False              # test flag
gunicorn_flag = False       # gunicorn flag
print('Parmstring = ',sys.argv)
print()
print('PYTHONUNBUFFERED = ',os.getenv('PYTHONUNBUFFERED'))

originalstdout = sys.stdout 
originalstderr = sys.stderr

#   if running in gunicorn redirect stdout, stderr to file
p = os.getenv('gw_web_gunicorn_flag')
if p == 'True' : gunicorn_flag = True

if gunicorn_flag is True:
    sys.stdout = open('gw_web.stdout', 'w')
    sys.stderr = open('gw_web.stderr', 'w')

#   if running in test mode
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
      
#   Create Flask and WebSocket instances
app = Flask(__name__)   # Flask instance
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25}
sock = Sock(app)        # Web Socket instance

#   Initialize websocket instances
ws = None
myws = None

#   Initialize array of clients
client_list = []

#   Build dictionary or parms
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
dateflag = False        # initialize datefla

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
listenthread = Thread(target = listen_to_gw_log)
listenthread.daemon = True
listenthread.start()

####################################################
#
#   Flask Routes for web server
#
####################################################

@app.route('/', methods=['GET', 'POST'])
def index():
#       render Garage Status Form based on garage door position        
        print("at Route / ")
        global garstatus
        global doorstate
        global invertlog
#       flush stdout, stderr buffers
        sys.stdout.flush()
        sys.stderr.flush()
#       reset invertlog flag
        invertlog = False

#       Get status of garage door and set status message

        if doorstate == "Open":
            garstatus = "is Open since " + octime.strftime("%l:%M:%S %P")
            if pinstatus == False:
                 garstatus = "Invalid PIN ..."
            garimg = 'static/images/GarageRed.gif'
            return render_template('GarageStatus.html', garname=gwdict['gwGarageName'], garstatus=garstatus,
                                       garimg=garimg, garcolor='red', hostname=hostname)

        elif doorstate == "Closed":
           garstatus = "is Closed since " + octime.strftime("%l:%M:%S %P")
           if pinstatus == False:
                garstatus = "Invalid PIN ..."
           garimg = 'static/images/GarageGreen.gif'
           return render_template('GarageStatus.html', garname=gwdict['gwGarageName'], garstatus=garstatus,
                                       garimg=garimg, garcolor='green', hostname=hostname)
           
        elif doorstate == "Opening":
            garstatus = "Is Opening"
            garimg = '/static/images/GarageQuestion.gif'
            return render_template('GarageStatus.html', garname=gwdict['gwGarageName'], garstatus=garstatus,
                                    garimg=garimg, garcolor='orange', hostname=hostname)

        elif doorstate == "Closing":
            garstatus = "Is Closing"
            garimg = '/static/images/GarageQuestion.gif'
            return render_template('GarageStatus.html', garname=gwdict['gwGarageName'], garstatus=garstatus,
                                    garimg=garimg, garcolor='orange', hostname=hostname)
        else:
            garstatus = "Status Unknown"
            garimg = '/static/images/GarageQuestion.gif'
            return render_template('GarageStatus.html', garname=gwdict['gwGarageName'], garstatus=garstatus,
                                    garimg=garimg, garcolor='orange', hostname=hostname)
                        
@app.route('/Garage', methods=['GET', 'POST'])
def Garage():
#       Garage Activation Code Entered
        global garstatus
        global pinstatus
        print("at Route /Garage")
        pin = request.form['garagecode']
        if pin == "" :
           pin = "NULL"
           garstatus = ''
           pinstatus = True

        print("PIN = " + pin)
        if pin == gwdict['gwCode']:  # Code if Password is correct
           garstatus = ''
           pinstatus = True
           print("Sending SIGUSR1 (10) to gw_log.py "+gw_log_pid)
           gwf.sendsignal(gw_log_pid, "10") 
        elif pin != "NULL":          # Code if Password is incorrect
           pinstatus = False         # invalid PIN   
           print("Sending SIGUSR1 (12) to gw_log.py "+gw_log_pid)           
           gwf.sendsignal(gw_log_pid, "12")
           print("Invalid PIN ...",pin)
           
        return redirect("/")   

@sock.route('/launch')
def launch(ws):
     global myws
     myws = ws
#     client_list.append(ws)     # add new client
     print('\nat /launch \nws = ',ws)
     loop = True
     while loop:
        data = ws.receive()
        cmd = ""
        cmdType = ""
        try:
            cmdArray = data.split("=")
            cmdType = cmdArray[0]
            cmd = cmdArray[1]
        except:
            print("Illegal cmd sent...")
            continue

        if cmdType == "GarageStatus":
             print(data)
             if cmd == "new client":     client_list.append(ws) # add new garage status client
             if cmd == "remove client" : 
                  client_list.remove(ws) # remove client
                  print(ws)
             print("Client List", len(client_list))
             for c in client_list:
                  print(c)
             print()

        if cmdType == "Admin":
            print("... received data from webadmin page ...")
            print(cmd,'\n')
            if cmd == 'reboot':
                reboot()
            if cmd == 'shutdown':
                shutdown()
            if cmd == 'close':
                close() 

     print('...loop exited...') 
     return "<p>Hello, World!</p>"

#       MyClock routes

@app.route('/MyClock')
def MyClock():
      print("at MyClock ...")
      return render_template('mygarageclock.html')

@app.route('/Show')
def Show():
    print("at Show\n")
    os.system(homedir + "/bin/myclock +s")
    return redirect('/MyClock')

@app.route('/Blank')
def Blank():
    print("at Blank\n")
    os.system(homedir + "/bin/myclock -s")
    return redirect('/MyClock')
    
@app.route('/ToggleMil')
def ToggleMil():
    global milflag
    print("at ToggleMil ",milflag)
    if milflag:
        milflag = False
        p = "-m"
    else:
        milflag = True
        p = "+m"
    cmd = homedir + "/bin/myclock "+p
    print(cmd)
    os.system(cmd)
    return redirect('/MyClock')

@app.route('/ToggleDate')
def ToggleDate():
    global dateflag
    print("at ToggleDate ",dateflag)
    if dateflag:
        dateflag = False
        p = "-d"
    else:
        dateflag = True
        p = "+d"
    cmd = homedir + "/bin/myclock "+p
    print(cmd)    
    os.system(cmd)
    return redirect('/MyClock')

@app.route('/Mil')
def Mil():
    print("at MIL\n")
    os.system(homedir + "/bin/myclock +m")
    return redirect('/MyClock')

@app.route('/notMIL')
def notMIL():
    print("at notMIL\n")
    os.system(homedir + "/bin/myclock -m")
    return redirect('/MyClock')

@app.route('/Dim')
def Dim():
    print("at Dim\n")
    os.system(homedir + "/bin/myclock -b 0")
    return redirect('/MyClock')

@app.route('/Bright')
def Bright():
    print("at Bright\n")
    os.system(homedir + "/bin/myclock -b 1")
    return redirect('/MyClock')

@app.route('/Segments')
def Segments():
    print("at Segments\n")
    os.system(homedir + "/bin/myclock -f")
    return redirect('/MyClock')

@app.route('/RestartClock')
def RestartClock():
    print("at RestartClock\n")
    os.system(homedir + "/bin/restartclock")
    return redirect('/MyClock')
        
@app.route('/Admin')
def Admin():
    print("at Admin")
    return render_template('webadmin.html')

#       end of MyClock routes

@app.route('/Log',methods=['GET', 'POST'])
def logfile():
        global invertlog
#        global logdata
        print('at Route /Log')
        logfname = gwdict['gwLogFile']
        ans = gwf.getlogdays(logfname)
        cnt = len(ans)

        if request.method == "POST":  # if at /Log get requested logday
             lday = request.form['logday']
             logdata = ans[cnt - 1 + int(lday)]
        else:
             lday = "0"
             logdata = ans[cnt - 1] # get last logday 

        # remove color escape sequences
        # Regex to match ANSI escape sequences
        # my pattern \x1b\[[0-9;]*m
        pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        logdata = re.sub(pattern,'', logdata)  # Remove escape sequences

        fmtdata = logdata
        
        z = datetime.now()
        logdate = z.strftime("%Y %b %d %H:%M:%S")

        return render_template('ShowLog.html', fmtdate=logdate, fmtdata=logdata,\
                                fmtlday=lday, fmtnumdays=cnt)

@app.route('/ShowParmForm')
def ShowParmForm():
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
        
        return render_template('parmform.html',
         p_gname = a,
         p_code = b,
         p_openwarn = c,
         p_closedoor = d,
         p_opentime = e,
         p_sendsms = f,
         p_boottime = g,
         p_logdays = h,
         p_phone1 = i,
         p_phone2 = j,
         p_url1 = k,
         p_url2 = l,
         p_led = m
        )
@app.route('/ProcParmForm',methods=['GET', 'POST'])
def ProcParmForm():
        gwdict['gwGarageName'] = request.form['frm_gname']
        gwdict['gwCode'] = request.form['frm_code']
        gwdict['gwOpenWarning'] = request.form['frm_warn']
        gwdict['gwCloseDoor'] = request.form['frm_close']
        gwdict['gwOpenTime'] = request.form['frm_opentime']
        gwdict['smsMsg'] = request.form['frm_sendsms']
        gwdict['gwBootTime'] = request.form['frm_boottime']
        gwdict['gwLogDays'] = request.form['frm_logdays']
        gwdict['sms_phone1'] = request.form['frm_phone1']
        gwdict['sms_phone2'] = request.form['frm_phone2']
        gwdict['sms_url1'] = request.form['frm_url1']
        gwdict['sms_url2'] = request.form['frm_url2']
        gwdict['pwm_duty'] = request.form['frm_led']
        
        gwf.update_ini(parmfile, gwdict, gwdictcomment)
        return redirect('/')

@app.route('/Parms')
def Parms():
        with open(parmfile, 'r') as f:
            pdata = f.read()
        return render_template('parms.html', parmdata=pdata)

@app.route('/TestSMS')
def test_sms():
        msg = '-\nGarage Monitor Application\n\nThis is a test message :\n'
        msg = msg + 'Open Time = ' + gwdict['gwOpenTime'] + ' minutes\n\n\n' 
        urlmsg = ''
        if gwdict['sms_url1'] != '' :
           urlmsg = urlmsg + "Local URL : " + gwdict['sms_url1'] +'\n\n\n'
        if gwdict['sms_url2'] != '' :
           urlmsg = urlmsg + "Remote URL : " + gwdict['sms_url2'] + '\n'
        msg = msg + urlmsg
        
        gwf.send_sms(gwdict, msg)
        return redirect('/')

##########################################################
#
#   Launch Flask Web Server
#
##########################################################
#   flush stdout, stderr buffers
sys.stdout.flush()
sys.stderr.flush()
now = datetime.now()
msg = now.strftime("\n%H:%M:%S gw_web.py at Launch Flask ...\n")
print(msg)

if __name__ == '__main__':
        app.run(debug=False, host='0.0.0.0', port=int(gwdict['gwPort']))

now = datetime.now()
msg = now.strftime("\n%H:%M:%S gw_web.py ended ...\n")
print(msg)
