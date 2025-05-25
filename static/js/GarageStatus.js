// my functions
async function sleep(ms) {
    await new Promise(resolve => setTimeout(resolve, 5000));
}
function sendmsg(msg){
    //socket.send('GarageStatus=' + 'new client');
    //confirm('msg ='+msg);
    console.log("sending : "+msg);
    socket.send(msg);
}    
function set_cookie(){
    const t = new Date();
    let x = fmtTime(t);
    localStorage.setItem("timestr", x)
}

function get_cookie(){
    const x = localStorage.getItem("timestr");
    document.getElementById('demofld').innerHTML = "timestr = " + x;
} 

// declare global variables
let octime = "",
    cmd,
    cmdArray,
    cmdtype,
    garimg,
    garstatus,
    msg
;
// establish web-socket
const socket = new WebSocket('ws://' + location.host + '/launch');
/*
    use either socket.addEventlistener('open', ev)
    or socket.onopen = function()
*/

msg = "GarageStatus=new client";
/* 
socket.addEventListener('open', ev => {
    console.log("Socket Opened");
    sendmsg();
})
 */
socket.onopen = function(){
    sendmsg(msg);
}
/* 
socket.onopen = (ev) => {
    console.log("new web socket");
    sendmsg();
}
 */


// listen for message from web server
socket.addEventListener('message', ev => {
        msg = ev.data;
        
        // parse and process message
        cmdArray = msg.split("=");
        cmdtype = cmdArray[0];
        cmd = cmdArray[1];
        
        if (cmdtype == 'PIN'){
            garstatus = 'Invalid PIN ... ' + cmd
            }

        if (cmdtype == 'time'){
            octime = cmd;
            }

        if (cmdtype == 'door'){
            let garimg;
            let garstatus;

            if (cmd == 'Open'){
                document.body.style.backgroundColor = 'red';
                garimg = '/static/images/GarageRed.gif';
                garstatus = 'Garage is Open since ' + octime;
            }
            if (cmd == 'Closed'){
                document.body.style.backgroundColor = 'green';
                garimg = '/static/images/GarageGreen.gif';
                garstatus = 'Garage is Closed since ' + octime;
            }

            if (cmd == 'Closing'){
                document.body.style.backgroundColor = 'orange';
                garimg = '/static/images/GarageQuestion.gif';
                garstatus = 'Garage is Closing';
            }
            if (cmd == 'Opening'){
                document.body.style.backgroundColor = 'orange';
                garimg = '/static/images/GarageQuestion.gif';
                garstatus = 'Garage is Opening';
            }

            // set garimg and garstatus
            document.getElementById('img1').src = garimg;
            document.getElementById('status').innerText = garstatus;

        }
        });

window.addEventListener("beforeunload", event => {
    // send message to gw_web.py to remove client from list
    socket.send('GarageStatus=' + 'remove client');
    socket.close()
});

/* 
const terminationEvent = 'onpagehide' in self ? 'pagehide' : 'unload';
window.addEventListener(terminationEvent, (event) => {
    if (event.persisted === false) {
        // client is gone
        socket.onclose = function () { };
        socket.close();
    }
}); */
