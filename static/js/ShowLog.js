// my functions
function sendwebmsg(msg){
    console.log('at sendwebmsg ...');
    
    const checker = setInterval(() => {
    console.log("Waiting for websocket ...",socket.readyState);
    
    if (socket.readyState === WebSocket.OPEN) {
        console.log("Websocket open ...");
        socket.send(msg)
        clearInterval(checker);  // Stop the loop
    }
    }, 100);
}    

function SetFocus(fld){
    const focusfld = document.getElementById(fld);
    const length = focusfld.value.length;
    focusfld.focus();
    focusfld.setSelectionRange(length, length);
   
}
// 
// establish web-socket
const socket = new WebSocket('ws://' + location.host + '/get_web_cmd');

// socket.onopen = () => {
//     console.log("new web socket " + socket);
//     // if logday is null send log=0 to webserver
//     if (logday == null){
//         sendwebmsg('Log=-2');
//     };
//     }

// listen for message from gw_web.py
socket.addEventListener('message', ev => {
    const jsonmsg = ev.data;
    console.log('received ' + jsonmsg);

    // Parse and process message
    const msg = JSON.parse(jsonmsg);

    if (msg.type === 'log') {
        const url = `/Log?` +
                    `logday=${encodeURIComponent(msg.logday)}&` +
                    `logdays=${encodeURIComponent(msg.logdays)}&` +
                    `loghdr=${encodeURIComponent(msg.loghdr)}&` +
                    `logdaycnt=${encodeURIComponent(msg.logdaycnt)}&` +
                    `logdata=${encodeURIComponent(msg.logdata)}`;
        
        // Redirect to /Log with parameters
        console.log("Redirecting to:", url);
        window.location.href = url;  // Uncomment to redirect
    }

});



    