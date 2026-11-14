#!/usr/bin/env node
// Print the sizing table for every gait and configuration.
//   node cli.js [--mass 75] [--height 1.75] [--payload 0] [--assist 0.3]
const path = require('path');
const sim = require('./exosim.js');
const norm = require(path.join(__dirname, '..', 'data', 'gait_norm.json'));
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? parseFloat(process.argv[i + 1]) : d; };
const opts = { bodyMass: arg('mass', 75), height: arg('height', 1.75), payload: arg('payload', 0), assist: arg('assist', 0.3) };
const f = (v, n = 1) => v.toFixed(n).padStart(7);
for (const cfg of Object.keys(sim.DESIGN.configs)) {
  console.log(`\n=== ${sim.DESIGN.configs[cfg].label} — masa ${sim.massModel(sim.DESIGN, cfg).total.toFixed(2)} kg ===`);
  for (const g of Object.keys(norm.gaits)) {
    const r = sim.simulate(norm, g, Object.assign({ config: cfg }, opts));
    console.log(`${g.padEnd(6)} v=${r.speed} m/s  belt(FK)=${r.kin.belt.toFixed(2)}  bat=${f(r.power.battery, 0)} W  autonomía=${f(r.endurance.hours, 2)} h /${f(r.endurance.km, 1)} km  metab: off ${f(100 * r.metabolic.offPct)}%  on ${f(100 * r.metabolic.netChangePct)}%`);
    for (const j of ['hip', 'knee', 'ankle']) {
      const J = r.joints[j];
      if (!J.active) { console.log(`   ${j.padEnd(5)} —  req pico ${f(Math.max(...J.req.map(Math.abs)))} Nm  ω pico ${f(J.peakOmega / (Math.PI / 180), 0)} °/s`); continue; }
      console.log(`   ${j.padEnd(5)} ${J.actuator.padEnd(18)} req ${f(Math.max(...J.req.map(Math.abs)))} Nm  exo ${f(J.peakTorque)} Nm  ω ${f(J.peakOmega / (Math.PI / 180), 0)} °/s  τuse ${f(100 * J.torqueUse, 0)}%  ωuse ${f(100 * J.speedUse, 0)}%  térmico ${f(100 * J.thermal, 0)}%  sat ${f(100 * J.saturated, 0)}%  entregado ${f(100 * J.delivered, 0)}%  P ${f(J.elecAvg, 0)} W  alivio ${f(100 * r.relief[j], 0)}%`);
    }
  }
}
