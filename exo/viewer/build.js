#!/usr/bin/env node
// Assemble the self-contained viewer: template.html + simulator + data -> index.html
const fs = require('fs');
const path = require('path');
const here = (...p) => path.join(__dirname, ...p);

const norm = JSON.parse(fs.readFileSync(here('..', 'data', 'gait_norm.json'), 'utf8'));
for (const g of Object.values(norm.gaits)) for (const c of Object.values(g.curves)) delete c.sd; // viewer only needs the means
const { sweep } = require(here('..', 'sim', 'sweep.js'));

const parts = {
  '/*__EXOSIM__*/': fs.readFileSync(here('..', 'sim', 'exosim.js'), 'utf8'),
  '/*__NORM__*/': 'const NORM = ' + JSON.stringify(norm) + ';',
  '/*__SWEEP__*/': 'const SWEEP = ' + JSON.stringify(sweep(0.3)) + ';',
};
let html = fs.readFileSync(here('template.html'), 'utf8');
for (const [k, v] of Object.entries(parts)) {
  if (!html.includes(k)) throw new Error('placeholder missing: ' + k);
  html = html.replace(k, () => v);
}
fs.writeFileSync(here('index.html'), html);
console.log('index.html', (html.length / 1024).toFixed(0) + ' kB');
