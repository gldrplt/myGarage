function updateTime(clockfld) {
  console.log('at updateTime()');
  function update() {
      const now = new Date();
      element.innerHTML = now.toLocaleTimeString();
  }
  const element = document.getElementById(clockfld);
  update(); // Initial update
  setInterval(update, 1000); // Update every second
}

// old functions to show time on web page
// function showTime() {
//   const today = new Date();
//   document.getElementById("clock").innerHTML =  fmtTime(today)
//   setTimeout(showTime, 1000);  // call showTime every second
// }

// function checkTime(i) {
//   if (i < 10) {i = "0" + i};  // add zero in front of numbers < 10
//   return i;
// }

// function fmtTime(t) { // format time object 12 hour am/pm string
//   let ampm ="";
//   let h = t.getHours();
//   let m = t.getMinutes();
//   let s = t.getSeconds();
//   if ( h > 11){ ampm = 'pm'}else{ ampm = 'am'}
//   if ( h > 12){ h = h - 12;}
//   m = checkTime(m);
//   s = checkTime(s);
//   let timestr =  h + ":" + m + ":" + s + " " + ampm;
//   return timestr;
// }
// **************************************************
