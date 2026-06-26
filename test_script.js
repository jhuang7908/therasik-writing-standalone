const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('api/static/console.html', 'utf8');
const dom = new JSDOM(html, { runScripts: "dangerously" });

// Setup minimal mocks
dom.window.localStorage = { getItem: () => null, setItem: () => {} };
dom.window.sessionStorage = { getItem: () => null, setItem: () => {} };

setTimeout(() => {
  console.log("Starting test...");
  
  // Simulate being on structural-vhvl
  dom.window.activateService("structural-vhvl");
  
  // User types in fv-vh
  dom.window.document.getElementById("fv-vh").value = "AAAAAAAAAA";
  console.log("fv-vh is now:", dom.window.document.getElementById("fv-vh").value);
  
  // User clicks Humanization
  dom.window.activateService("vhvl-humanization");
  
  console.log("vhvl-vh is now:", dom.window.document.getElementById("vhvl-vh").value);
  
  // Try with pending species
  dom.window.document.getElementById("vhvl-vh").value = "BBBBBBBBBB";
  dom.window.activateService("mouse-humanization");
  console.log("vhvl-vh after mouse-humanization is now:", dom.window.document.getElementById("vhvl-vh").value);
}, 100);
