// node --test exo/sim
const test = require('node:test');
const assert = require('node:assert/strict');
const sim = require('./exosim.js');
const norm = require('../data/gait_norm.json');
const GAITS = Object.keys(norm.gaits);
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg || ''} expected ${b} ± ${tol}, got ${a}`);

test('normative data is physically plausible', () => {
  for (const g of GAITS) {
    const c = norm.gaits[g].curves;
    const fv = c.grf_v.mean, bw = 2 * fv.reduce((a, b) => a + b, 0) / fv.length / sim.G;
    near(bw, 1, 0.08, `${g}: mean vertical GRF over a stride, in body weights`);
    assert.equal(fv.length, sim.N);
  }
  const ankle = Math.max(...norm.gaits.walk.curves.ankle_mom.mean);
  assert.ok(ankle > 1.2 && ankle < 1.7, `walking ankle moment peak ${ankle} Nm/kg`);
  assert.ok(Math.max(...norm.gaits.run35.curves.grf_v.mean) > 2 * sim.G, 'running peak GRF above 2 BW');
});

test('spectral derivative of a sine', () => {
  const T = 0.8, y = Array.from({ length: sim.N }, (_, i) => Math.sin(2 * Math.PI * i / sim.N));
  const d = sim.deriv(y, T);
  for (let i = 0; i < sim.N; i += 7) near(d[i], 2 * Math.PI / T * Math.cos(2 * Math.PI * i / sim.N), 1e-9);
});

test('actuator envelope passes through the vendor points', () => {
  for (const a of Object.values(sim.ACTUATORS)) {
    near(sim.torqueLimit(a, a.wRated, true), a.tauRated, 1e-9, a.name + ' rated point');
    near(sim.torqueLimit(a, a.wNoLoad, true), 0, 1e-9, a.name + ' no-load');
    assert.equal(sim.torqueLimit(a, 0, true), a.tauPeak);
    assert.equal(sim.torqueLimit(a, a.wNoLoad * 2, false), a.tauPeak, 'braking is not voltage limited');
  }
});

test('kinematics: feet stay on or above the ground, walking has no flight, running does', () => {
  for (const g of GAITS) {
    const k = sim.kinematics(norm.gaits[g], 1.75);
    for (const f of k.frames) for (const leg of [f.R, f.L]) {
      assert.ok(f.py + Math.min(leg.heel[1], leg.ball[1]) > -0.03, `${g}: foot through the floor`);
    }
    if (g === 'walk') assert.equal(k.flightFraction, 0); else assert.ok(k.flightFraction > 0.1, `${g} flight ${k.flightFraction}`);
  }
});

test('kinematics: reconstructed speed is close to the treadmill speed', () => {
  const w = norm.gaits.walk; near(sim.kinematics(w, w.height).belt / w.speed, 1, 0.08, 'walk');
  // sagittal-only reconstruction is known to fall short in running (no pelvis rotation); keep it bounded
  for (const g of ['run25', 'run35', 'run45']) {
    const r = sim.kinematics(norm.gaits[g], norm.gaits[g].height).belt / norm.gaits[g].speed;
    assert.ok(r > 0.8 && r < 1.05, `${g} ratio ${r}`);
  }
});

test('mass model adds up and follows the configuration', () => {
  for (const cfg of Object.keys(sim.DESIGN.configs)) {
    const m = sim.massModel(sim.DESIGN, cfg);
    near(m.total, m.items.reduce((a, it) => a + it.mass * it.qty, 0), 1e-9);
    near(m.total, Object.values(m.byLoc).reduce((a, b) => a + b, 0), 1e-9);
  }
  assert.ok(sim.massModel(sim.DESIGN, 'full').total > sim.massModel(sim.DESIGN, 'run').total);
  assert.equal(sim.massModel(sim.DESIGN, 'ankle').byLoc.thigh, 0);
});

test('with zero assistance and no self-carry the exo applies no torque', () => {
  const r = sim.simulate(norm, 'walk', { assist: 0, selfCarry: 0 });
  for (const j of ['hip', 'knee', 'ankle']) {
    assert.equal(Math.max(...r.joints[j].exo.map(Math.abs)), 0);
    assert.deepEqual(r.joints[j].human, r.joints[j].req);
  }
  assert.ok(r.metabolic.netChangePct > 0, 'dead weight must cost energy');
});

test('the exo never pushes against its command and the ankle only plantarflexes', () => {
  for (const g of GAITS) for (const cfg of ['full', 'run']) {
    const r = sim.simulate(norm, g, { config: cfg, assist: 0.5 });
    for (const j of ['hip', 'knee', 'ankle']) {
      const J = r.joints[j]; if (!J.active) continue;
      const a = sim.ACTUATORS[sim.DESIGN.joints[j].actuator];
      assert.ok(J.peakAct <= a.tauPeak + 1e-9, `${g}/${j} above peak torque`);
      assert.ok(J.delivered <= 1 + 1e-9);
      if (j === 'ankle') assert.ok(Math.min(...J.exo) >= 0);
    }
  }
});

test('heavier wearer and payload raise the required moments; assistance lowers the human share', () => {
  const peak = (r) => Math.max(...r.joints.ankle.req);
  assert.ok(peak(sim.simulate(norm, 'walk', { bodyMass: 90 })) > peak(sim.simulate(norm, 'walk', { bodyMass: 60 })));
  assert.ok(peak(sim.simulate(norm, 'walk', { payload: 20 })) > peak(sim.simulate(norm, 'walk', {})));
  const lo = sim.simulate(norm, 'walk', { assist: 0.1 }), hi = sim.simulate(norm, 'walk', { assist: 0.4 });
  for (const j of ['hip', 'knee', 'ankle']) assert.ok(hi.relief[j] > lo.relief[j]);
  assert.ok(hi.power.battery > lo.power.battery);
});

test('energy bookkeeping: endurance = usable energy / battery power', () => {
  const r = sim.simulate(norm, 'run35', { config: 'run' });
  near(r.endurance.hours * r.power.battery, r.endurance.usableWh, 1e-6);
  near(r.endurance.usableWh, 240 * 0.85, 1e-9);
});
