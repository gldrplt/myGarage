// functions to control web server

// establish web-socket
const socket = new WebSocket('ws://' + location.host + '/get_web_cmd');

function goback() {
    history.back();
}

function shutdown() {
    if (confirm("Are you sure you want to shutdown?") == true){
//        alert("... You confirmed shutdown ...");
        socket.send('Admin=shutdown')
        history.back();
    } else {
        alert("... You CANCELLED shutdown ...");
    }
}

function closegw() {
    if (confirm("Are you sure you want to close webserver?") == true){
//        alert("... You confirmed close webserver ...");
        socket.send('Admin=close')
        history.back();
    } else {
        alert("... You CANCELLED close webserver ...");
    }    
}

function reboot() {
    if (confirm("Are you sure you want to reboot?") == true){
//        alert("... You confirmed reboot ...");
        socket.send('Admin=reboot')
        history.back();
    } else {
        alert("... You CANCELLED reboot ...");
    }
}

