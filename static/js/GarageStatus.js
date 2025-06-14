// declare variables
let [mybrowser, myos, isMobile] = getDeviceAndBrowserInfo();
console.log(mybrowser, myos, isMobile);

// my functions
async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function sendgaragecode(code) {
  console.log("at sendgaragecode");
  const msg = "GarCode=" + code;
  console.log("sending : " + msg);
  socket.send(msg);
}

function sendwebmsg(msg) {
  console.log("at sendwebmsg ...");
  socket.send(msg);
}

function set_cookie() {
  const t = new Date();
  let x = fmtTime(t);
  localStorage.setItem("timestr", x);
}

function get_cookie() {
  const x = localStorage.getItem("timestr");
  document.getElementById("demofld").innerHTML = "timestr = " + x;
}

function SetFocus(fld) {
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
  else if (ua.includes("MSIE") || ua.includes("Trident"))
    browser = "Internet Explorer";

  let os = "Unknown";
  if (ua.includes("Win")) os = "Windows";
  else if (ua.includes("Mac")) os = "MacOS";
  else if (ua.includes("X11")) os = "UNIX";
  else if (ua.includes("Linux")) os = "Linux";
  else if (/Android/.test(ua)) os = "Android";
  else if (/iPhone|iPad|iPod/.test(ua)) os = "iOS";

  const isMobile = /Mobi|Android/i.test(ua);

  return [browser, os, isMobile];
}
function logResize() {
  let el = document.getElementById("wrapper");
  console.log("**************************************");
  console.log("   wrapper clientWidth:", el.clientWidth);
  console.log("   wrapper clientHeight:", el.clientHeight);
  console.log("   wrapper offsetHeight:", el.offsetHeight);
  console.log("wrapper bounding height:", el.getBoundingClientRect().height);
  console.log("        viewport height:", window.innerHeight);
  console.log("");
}
function scaleResize() {
  
  if (isMobile == false) {
    let el = document.getElementById("wrapper");
    let wrapperheight = el.offsetHeight;
    let viewportheight = window.innerHeight;
    let scale = Math.min((viewportheight / wrapperheight), 1);
    
    el.style.transform = `scale(${scale})`;  
    //el.style.transform = 'scale(0.6)';
    el.style.transformOrigin = "top center";
    console.log('setting scale to ' + scale)
  }
}

// establish web-socket
const socket = new WebSocket("ws://" + location.host + "/get_web_cmd");

socket.onopen = () => {
  console.log("new web socket " + socket);
};

// listen for message from web server
socket.addEventListener("message", (ev) => {
  jsonmsg = ev.data;
  console.log("received " + jsonmsg);
  // parse and process message
  const msg = JSON.parse(jsonmsg);

  if (msg.type == "door") {
    // set garimg, garcolor and garstatus
    document.getElementById("wrapper").style.backgroundColor = msg.color;
    document.getElementById("img1").src = msg.image;
    document.getElementById("status").innerText = msg.status;
  }
  if (msg.type == "pin") {
    document.getElementById("status").innerText = "Invalid PIN ...";
  }
});

//  monitor resize event
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    logResize();
    scaleResize();
  }, 200); // Adjust debounce delay as needed
});

// wait to run code until page loads
window.addEventListener("load", function () {
  console.log("GarageStatus.html fully loaded and parsed!");
  // Your code here
  // show key height data
  logResize();
  scaleResize();

  console.log("create Listener for garagecode");
  const mygaragecode = document.getElementById("garagecode");
  mygaragecode.addEventListener("blur", function () {
    const code = mygaragecode.value;
    sendgaragecode(code);
    console.log("setting garagecode to blank");
    mygaragecode.value = "";
  });

  const input = document.getElementById("garagecode");
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      input.blur(); // removes focus from the input field
    }  
  });


});

