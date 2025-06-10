// my functions
async function sleep(ms) {
    await new Promise(resolve => setTimeout(resolve, ms));
}

function sendgaragecode(code){
    console.log('at sendgaragecode');
    const msg = "GarCode=" + code;
    console.log("sending : " + msg);
    socket.send(msg);
}

function sendwebmsg(msg){
    console.log('at sendwebmsg ...');
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

function SetFocus(fld){
    const focusfld = document.getElementById(fld);
    const length = focusfld.value.length;
    focusfld.focus();
    focusfld.setSelectionRange(length, length);
   
}

// establish web-socket
const socket = new WebSocket('ws://' + location.host + '/get_web_cmd');

socket.onopen = () => {
    console.log("new web socket " + socket);
    }


// listen for message from web server
socket.addEventListener('message', ev => {
        jsonmsg = ev.data;
        console.log('received ' + jsonmsg);
        // parse and process message
        const msg=JSON.parse(jsonmsg);

        if (msg.type == 'door'){
            // set garimg, garcolor and garstatus
            document.body.style.backgroundColor = msg.color;
            document.getElementById('img1').src = msg.image;
            document.getElementById('status').innerText = msg.status;
        }
        if (msg.type == 'pin'){
            document.getElementById('status').innerText = 'Invalid PIN ...';
        }
        if (msg.type == 'log'){
            debugger;
            localStorage.setItem("loghdr", msg.loghdr);
            localStorage.setItem("logday", msg.logday);
            localStorage.setItem("logdata", msg.logdata);
            console.log(msg)
        }
    });