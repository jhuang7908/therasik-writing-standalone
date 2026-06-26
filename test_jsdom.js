const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('api/static/console.html', 'utf8');

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  url: "http://localhost",
  beforeParse(win) {
    win.requestAnimationFrame = (cb) => setTimeout(cb, 0);
  }
});

dom.window.localStorage = { getItem: () => null, setItem: () => {} };
dom.window.sessionStorage = { getItem: () => null, setItem: () => {} };

setTimeout(() => {
  const win = dom.window;
  const doc = win.document;

  console.log("--- Initial state ---");
  console.log("Current service:", win.state.service);

  console.log("\n--- Activating segmentation-vhvl ---");
  win.activateService("segmentation-vhvl");
  
  const segVh = doc.getElementById("seg-vh");
  segVh.value = "MUTATED_VH_SEQUENCE";
  console.log("User typed into seg-vh:", segVh.value);

  console.log("\n--- Activating mouse-humanization (from sidebar) ---");
  win.activateService("mouse-humanization");
  
  const vhvlVh = doc.getElementById("vhvl-vh");
  console.log("vhvl-vh value is:", vhvlVh.value);

  console.log("\n--- Let's do it again with activateHumanizationFromLastDonor ---");
  win.activateService("segmentation-vhvl");
  doc.getElementById("seg-vh").value = "ANOTHER_MUTATED_SEQUENCE";
  win.activateHumanizationFromLastDonor();
  console.log("vhvl-vh value is:", doc.getElementById("vhvl-vh").value);

}, 100);
