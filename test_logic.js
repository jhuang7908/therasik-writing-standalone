const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const dom = new JSDOM(`<!DOCTYPE html><p>Hello world</p>`);
const document = dom.window.document;

let state = {
  sharedVh: null,
  sharedVhh: null
};

const getVal = id => { const el = document.getElementById(id); return el ? el.value.trim() : ""; };

function capture() {
  const vh = ["vhvl-vh", "seg-vh"].map(getVal).find(v => v);
  if (vh) state.sharedVh = vh;
  
  const vhh = ["vhh-seq", "vhh-seg-seq"].map(getVal).find(v => v);
  if (vhh) state.sharedVhh = vhh;
}

function populate() {
  let populated = false;

  if (state.sharedVh) {
    ["vhvl-vh", "seg-vh"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedVh; populated = true; }
    });
  }

  if (state.sharedVhh) {
    ["vhh-seq", "vhh-seg-seq"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = state.sharedVhh; populated = true; }
    });
  }

  if (populated) {
    state.sharedVh = null;
    state.sharedVhh = null;
  }
}

// 1. Simulate user on segmentation page
document.body.innerHTML = '<textarea id="seg-vh">MUTATED_VH</textarea>';
capture();
console.log("After capture on seg-vh, state:", state);

// 2. Simulate navigation to humanization page
document.body.innerHTML = '<textarea id="vhvl-vh"></textarea>';
// (loadServiceDemo happens here)
document.getElementById("vhvl-vh").value = "DEMO_SEQUENCE";
console.log("After loadServiceDemo, vhvl-vh:", document.getElementById("vhvl-vh").value);

populate();
console.log("After populate, vhvl-vh:", document.getElementById("vhvl-vh").value);
console.log("State after populate:", state);

