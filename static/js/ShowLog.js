// my functions
function sendwebmsg(msg){
    console.log('at sendwebmsg msg: ',msg);
    if (msg === "Log=") {
        console.log('Logday is null');
        return};
    const checker = setInterval(() => {
        let cnt = 0;
        console.log(cnt,"  Waiting for websocket ...",socket.readyState);
        if (socket.readyState === WebSocket.OPEN) {
            console.log("Websocket open ...");
            socket.send(msg)
            clearInterval(checker);  // Stop the loop
            }
            cnt = cnt + 1;
        }, 50);
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
    console.log("new web socket for ShowLog " + socket);
    }

// listen for message from gw_web.py
socket.addEventListener('message', ev => {
    const jsonmsg = ev.data;
    console.log('received ' + jsonmsg);

    // Parse and process message
    const msg = JSON.parse(jsonmsg);
    // update webpage elements
    if (msg.type === 'LogData') {
            document.getElementById('logday').value = msg.logday;
            document.getElementById('loghdr').innerHTML = msg.loghdr;
            document.getElementById('logdata').innerHTML = msg.logdata;
            document.getElementById('loghdr2').innerHTML = '(There are ' + msg.logdaycnt +' days in log file)';
            SetFocus('logday');
    }
});

// wait to run code until page loads
window.addEventListener("load", function () {
  console.log("GarageStatus.html fully loaded and parsed!");
    // Your code here
    // first time, get logdata for today
    sendwebmsg('Log=0');

    // create listener for logday field
    console.log('create Listener for logday');
    mylogform = document.getElementById("logday");
    mylogform.addEventListener('blur', function() {
        
        const logday = mylogform.value;
        const msg = 'Log=' + logday
		sendwebmsg(msg);
    });
    // if Enter key pressed
    const input = document.getElementById("logday");
    input.addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
            input.blur(); // removes focus from the input field
//            SetFocus('logday');
        }
    });






});