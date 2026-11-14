#!/usr/bin/env node
// Actuator selection sweep: every candidate at every joint, across all gaits.
// Worst case over gaits is reported. node sweep.js [--assist 0.3]
const sim = require('./exosim.js'), norm = require('../data/gait_norm.json');
const ai = process.argv.indexOf('--assist'); const assist = ai > 0 ? parseFloat(process.argv[ai + 1]) : 0.3;
const gaits = Object.keys(norm.gaits);
const cands = { hip: [['RS03', 1], ['AK109', 1], ['RS04', 1]], knee: [['RS03', 1], ['AK109', 1], ['RS04', 1]],
  ankle: [['RS03', 2], ['RS03', 3], ['AK109', 2], ['AK109', 2.5], ['AK109', 3], ['AK109', 4], ['RS04', 1.5], ['RS04', 2]] };
const cfgFor = { hip: 'run', knee: 'full', ankle: 'run' };
const p = (v) => (100 * v).toFixed(0).padStart(4) + '%';
function sweep(a) {
  const rows = [];
  for (const j of Object.keys(cands)) for (const [act, ratio] of cands[j]) {
    const d = JSON.parse(JSON.stringify(sim.DESIGN)); d.joints[j] = Object.assign({}, d.joints[j], { actuator: act, ratio });
    const w = { thermal: 0, torqueUse: 0, speedUse: 0, saturated: 0, delivered: 1 }, per = {};
    for (const g of gaits) {
      const J = sim.simulate(norm, g, { config: cfgFor[j], assist: a, design: d }).joints[j];
      for (const k of ['thermal', 'torqueUse', 'speedUse', 'saturated']) w[k] = Math.max(w[k], J[k]);
      w.delivered = Math.min(w.delivered, J.delivered); per[g] = J.thermal;
    }
    const ok = w.thermal <= 1 && w.speedUse <= 1 && w.delivered >= 0.97;
    rows.push({ joint: j, actuator: act, ratio, mass: sim.ACTUATORS[act].mass, worst: w, per, ok });
  }
  return rows;
}
module.exports = { sweep };
if (require.main === module) {
  console.log(`Asistencia ${assist * 100}% — peor caso sobre ${gaits.join(', ')}`);
  for (const r of sweep(assist)) console.log(`${r.joint.padEnd(6)}${r.actuator.padEnd(6)} x${String(r.ratio).padEnd(4)} ${r.mass.toFixed(2)} kg  térmico${p(r.worst.thermal)} (walk${p(r.per.walk)} run35${p(r.per.run35)})  par${p(r.worst.torqueUse)}  vel${p(r.worst.speedUse)}  sat${p(r.worst.saturated)}  entregado${p(r.worst.delivered)}  ${r.ok ? 'OK' : '--'}`);
}
