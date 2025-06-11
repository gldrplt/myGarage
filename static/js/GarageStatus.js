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
function getDeviceAndBrowserInfo() {
    const ua = navigator.userAgent;

    let browser = "Unknown";
    if (ua.includes("Firefox")) browser = "Firefox";
    else if (ua.includes("Edg")) browser = "Edge";
    else if (ua.includes("Chrome")) browser = "Chrome";
    else if (ua.includes("Safari")) browser = "Safari";
    else if (ua.includes("MSIE") || ua.includes("Trident")) browser = "Internet Explorer";

    let os = "Unknown";
    if (ua.includes("Win")) os = "Windows";
    else if (ua.includes("Mac")) os = "MacOS";
    else if (ua.includes("X11")) os = "UNIX";
    else if (ua.includes("Linux")) os = "Linux";
    else if (/Android/.test(ua)) os = "Android";
    else if (/iPhone|iPad|iPod/.test(ua)) os = "iOS";

    const isMobile = /Mobi|Android/i.test(ua);
    
    return [
        browser,
        os,
        isMobile
    ]
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
            document.getElementById("wrapper").style.backgroundColor = msg.color;
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