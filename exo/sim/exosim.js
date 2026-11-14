/*
 * exosim.js — first-order design simulator for a modular lower-limb exoskeleton.
 *
 * One implementation shared by Node (tests, CLI) and the browser viewer.
 *
 * What it is: inverse-dynamics sizing on measured human gait. Joint angles, net
 *   joint moments and ground reaction forces come from public datasets (see
 *   ../data/gait_norm.json). The exoskeleton is added as mass + torque sources
 *   and every actuator is checked against its torque / speed / thermal envelope.
 * What it is NOT: a predictive simulation. The wearer is assumed to keep the
 *   same kinematics; human adaptation is not modelled.
 *
 * Sagittal plane. x forward, y up. Conventions:
 *   angles  hip +flexion, knee +flexion, ankle +dorsiflexion
 *   moments hip +extensor, knee +extensor, ankle +plantarflexor (internal)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ExoSim = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const G = 9.81;
  const N = 100; // samples per stride
  const RPM = Math.PI / 30;
  const DEG = Math.PI / 180;

  // ---------------------------------------------------------------- actuators
  // "spec" fields are vendor-listed; "assumed" fields are engineering estimates
  // that must be replaced by bench measurements (see README).
  const ACTUATORS = {
    RS04: {
      name: 'RobStride 04', gear: 9,
      tauPeak: 120, tauRated: 40, wNoLoad: 200 * RPM, wRated: 167 * RPM, mass: 1.42, price: 450, // spec
      rotorInertia: 1.4e-4, km: 4.5, coulomb: 0.5, viscous: 0.02, // assumed
    },
    RS03: {
      name: 'RobStride 03', gear: 9,
      tauPeak: 60, tauRated: 20, wNoLoad: 195 * RPM, wRated: 180 * RPM, mass: 0.88, price: 250, // spec
      rotorInertia: 0.8e-4, km: 3.0, coulomb: 0.35, viscous: 0.015, // assumed
    },
    AK109: {
      name: 'CubeMars AK10-9 V3', gear: 9,
      tauPeak: 53, tauRated: 18, wNoLoad: 320 * RPM, wRated: 235 * RPM, mass: 0.94, price: 900, // spec
      rotorInertia: 1.0e-4, // spec (1002 g·cm²)
      km: 3.2, coulomb: 0.4, viscous: 0.012, // assumed
    },
  };

  // Torque available at speed w when motoring. A straight line through the
  // no-load point and the rated point (voltage limit), capped by the current
  // limit (peak torque). Braking is not voltage-limited.
  function torqueLimit(act, w, motoring) {
    if (!motoring) return act.tauPeak;
    const slope = act.tauRated / (act.wNoLoad - act.wRated);
    return Math.max(0, Math.min(act.tauPeak, slope * (act.wNoLoad - Math.abs(w))));
  }

  // ---------------------------------------------------------------- design
  // loc: where the mass rides. d: distance from the proximal joint as a
  // fraction of the segment length (thigh: from hip, shank: from knee).
  const DESIGN = {
    busVoltage: 48.1, // 13S Li-ion nominal
    // hot-swappable 13S1P packs of 21700 cells (5 Ah): 240 Wh and ~1.15 kg each
    batteryPack: { wh: 240, usable: 0.85, mass: 1.15, label: '13S1P 21700 (5 Ah, 240 Wh)' },
    housekeepingW: 15, // computer, sensors, comms
    idleW: 3, // per actuator drive
    gearEff: 0.9, inverterEff: 0.95, regenEff: 0.7,
    joints: {
      hip: { actuator: 'RS04', ratio: 1, bidirectional: true },
      knee: { actuator: 'RS04', ratio: 1, bidirectional: true },
      // actuator on the proximal shank pulls a rope on a heel lever: lever / drum radius
      ankle: { actuator: 'AK109', ratio: 2.5, bidirectional: false },
    },
    // actuator masses are added automatically from the joint table
    structure: [
      { module: 'core', name: 'Cinturón lumbar + arnés', mass: 0.70, loc: 'waist', qty: 1 },
      { module: 'core', name: 'Electrónica, cableado, paro de emergencia', mass: 0.90, loc: 'waist', qty: 1 },
      { module: 'hip', name: 'Marco pélvico (CF + Ti), bisagras de abducción', mass: 1.10, loc: 'waist', qty: 1 },
      { module: 'hip', name: 'Eslabón de muslo + abrazadera', mass: 0.45, loc: 'thigh', d: 0.5, qty: 2 },
      { module: 'knee', name: 'Extensión de muslo hasta rodilla', mass: 0.25, loc: 'thigh', d: 0.8, qty: 2 },
      { module: 'knee', name: 'Eslabón de pierna + abrazadera', mass: 0.40, loc: 'shank', d: 0.4, qty: 2 },
      { module: 'ankle', name: 'Bastidor tibial + tambor y cuerda', mass: 0.35, loc: 'shank', d: 0.35, qty: 2 },
      { module: 'ankle', name: 'Plantilla de carbono + palanca de talón', mass: 0.30, loc: 'foot', qty: 2 },
    ],
    // where each joint's actuator rides
    actuatorMount: {
      hip: { loc: 'waist' },
      knee: { loc: 'thigh', d: 1.0 },
      ankle: { loc: 'shank', d: 0.25 },
    },
    configs: {
      full: { label: 'Completo (cadera + rodilla + tobillo)', modules: ['core', 'hip', 'knee', 'ankle'], packs: 2 },
      run: { label: 'Carrera (cadera + tobillo)', modules: ['core', 'hip', 'ankle'], packs: 1 },
      hip: { label: 'Solo cadera', modules: ['core', 'hip'], packs: 1 },
      ankle: { label: 'Solo tobillo', modules: ['core', 'ankle'], packs: 1 },
    },
  };

  // Metabolic bookkeeping (Mooney, Rouse & Herr 2014 "augmentation factor",
  // generalised): 1 W of net-positive exo joint power is worth 1/0.41 W of
  // metabolic power; carried mass costs k_loc * (net metabolic W/kg) per kg.
  const METAB = {
    eta: 0.41,
    // W per kg of added mass while walking at ~1.25-1.5 m/s
    betaWalk: { waist: 3.3, thigh: 5.6, shank: 5.6, foot: 14.8 },
    netWalk: 3.0, // W/kg net metabolic rate, walking 1.25 m/s (typical)
    runCot: 3.8, // J/kg/m net cost of transport, running (typical)
  };

  // ---------------------------------------------------------------- numerics
  const COS = [], SIN = [];
  for (let k = 0; k < N; k++) { COS.push(Math.cos(2 * Math.PI * k / N)); SIN.push(Math.sin(2 * Math.PI * k / N)); }

  // d/dt of a periodic signal sampled N times over period T (spectral, band-limited)
  function deriv(y, T, maxHarm) {
    const H = maxHarm || 16, out = new Array(N).fill(0);
    for (let h = 1; h <= H; h++) {
      let a = 0, b = 0;
      for (let i = 0; i < N; i++) { const k = (h * i) % N; a += y[i] * COS[k]; b += y[i] * SIN[k]; }
      a *= 2 / N; b *= 2 / N;
      const w = 2 * Math.PI * h / T;
      for (let i = 0; i < N; i++) { const k = (h * i) % N; out[i] += w * (-a * SIN[k] + b * COS[k]); }
    }
    return out;
  }
  const shift = (y, s) => y.map((_, i) => y[(i + s) % N]);
  const mean = (y) => y.reduce((a, b) => a + b, 0) / y.length;
  const rms = (y) => Math.sqrt(mean(y.map((v) => v * v)));
  const maxAbs = (y) => y.reduce((a, b) => Math.max(a, Math.abs(b)), 0);
  const smooth01 = (x) => { const t = Math.max(0, Math.min(1, x)); return t * t * (3 - 2 * t); };

  // ---------------------------------------------------------------- body
  function anthropometry(height) {
    return {
      thigh: 0.245 * height, shank: 0.246 * height,
      ankleH: 0.039 * height + 0.02, // + shoe sole
      heelBack: 0.030 * height, ballFwd: 0.085 * height, toeLen: 0.033 * height,
      trunk: 0.30 * height, hipWidth: 0.10 * height,
    };
  }

  // Segment angles and joint positions of one leg relative to the hip.
  function legFK(seg, hip, knee, ankle, tilt) {
    const tt = hip - tilt, ts = tt - knee, tf = ts + ankle;
    const kx = seg.thigh * Math.sin(tt), ky = -seg.thigh * Math.cos(tt);
    const ax = kx + seg.shank * Math.sin(ts), ay = ky - seg.shank * Math.cos(ts);
    const ux = Math.cos(tf), uy = Math.sin(tf), dx = Math.sin(tf), dy = -Math.cos(tf);
    return {
      tt, ts, tf, knee: [kx, ky], ankle: [ax, ay],
      heel: [ax - seg.heelBack * ux + seg.ankleH * dx, ay - seg.heelBack * uy + seg.ankleH * dy],
      ball: [ax + seg.ballFwd * ux + seg.ankleH * dx, ay + seg.ballFwd * uy + seg.ankleH * dy],
    };
  }

  // Whole-body sagittal kinematics on a treadmill: pelvis height from foot
  // contact (stance) and ballistic flight (running), fore-aft from the
  // no-slip condition of the stance foot. Returns per-sample frames.
  //
  // The running dataset has no pelvis angle. A constant anterior tilt is
  // calibrated so that the pelvis leaves the ground and lands at the same
  // height, which is what a ballistic flight phase requires.
  function kinematics(gait, height, tiltOffset) {
    const c = gait.curves, off = (tiltOffset || 0) * DEG;
    if (c.pelvis_tilt) return solveKinematics(gait, height, c.pelvis_tilt.mean.map((v) => v * DEG + off));
    let best = null;
    for (let t = 0; t <= 30; t += 0.5) {
      const k = solveKinematics(gait, height, new Array(N).fill(t * DEG));
      if (!best || Math.abs(k.flightDrop) < Math.abs(best.flightDrop)) best = k;
    }
    return off ? solveKinematics(gait, height, best.tilt.map((v) => v + off)) : best;
  }

  function solveKinematics(gait, height, tilt) {
    const c = gait.curves, T = gait.stride_time, seg = anthropometry(height);
    const hip = c.hip_ang.mean.map((v) => v * DEG), knee = c.knee_ang.mean.map((v) => v * DEG),
      ankle = c.ankle_ang.mean.map((v) => v * DEG), fv = c.grf_v.mean;
    const R = [], L = [];
    for (let i = 0; i < N; i++) R.push(legFK(seg, hip[i], knee[i], ankle[i], tilt[i]));
    for (let i = 0; i < N; i++) L.push(R[(i + N / 2) % N]);
    const fvL = shift(fv, N / 2);
    // a foot counts as planted once it carries ~10 % of body weight
    const wR = fv.map((v) => smooth01((v - 0.5) / 1.5)), wL = fvL.map((v) => smooth01((v - 0.5) / 1.5));

    // contact point of a foot: soft-min between heel and ball
    const contact = (f) => {
      const e = 0.006, lo = Math.min(f.heel[1], f.ball[1]), a = Math.exp(-(f.heel[1] - lo) / e), b = Math.exp(-(f.ball[1] - lo) / e);
      return { wh: a / (a + b), wb: b / (a + b), low: lo };
    };
    const cR = R.map(contact), cL = L.map(contact);
    const series = (legs, key, ax) => legs.map((f) => f[key][ax]);
    const vel = (legs, cs) => {
      const vh = deriv(series(legs, 'heel', 0), T), vb = deriv(series(legs, 'ball', 0), T);
      return vh.map((v, i) => cs[i].wh * v + cs[i].wb * vb[i]);
    };
    const vcR = vel(R, cR), vcL = vel(L, cL);

    const py = new Array(N).fill(null), vrel = new Array(N).fill(null);
    for (let i = 0; i < N; i++) {
      const w = wR[i] + wL[i];
      if (w > 0.05) {
        py[i] = (wR[i] * -cR[i].low + wL[i] * -cL[i].low) / w;
        vrel[i] = (wR[i] * vcR[i] + wL[i] * vcL[i]) / w; // contact-point velocity relative to pelvis
      }
    }
    // flight phases: ballistic height, constant fore-aft velocity
    const dt = T / N;
    let flight = 0, flightDrop = 0;
    for (let i = 0; i < N; i++) {
      if (py[i] !== null || py[(i + N - 1) % N] === null) continue;
      let n = 0; while (py[(i + n) % N] === null) n++;
      const a = (i + N - 1) % N, b = (i + n) % N, Tf = (n + 1) * dt;
      flightDrop = py[a] - py[b];
      for (let k = 1; k <= n; k++) {
        const t = k * dt, j = (i + k - 1) % N;
        py[j] = py[a] + (py[b] - py[a]) * t / Tf + 0.5 * G * t * (Tf - t);
        vrel[j] = vrel[a] + (vrel[b] - vrel[a]) * t / Tf;
        flight++;
      }
    }
    const belt = -mean(vrel); // kinematically consistent treadmill speed
    const px = new Array(N).fill(0);
    for (let i = 1; i < N; i++) px[i] = px[i - 1] + (-belt - 0.5 * (vrel[i] + vrel[i - 1])) * dt;
    const mx = mean(px);
    const frames = [];
    for (let i = 0; i < N; i++) frames.push({ px: px[i] - mx, py: py[i], R: R[i], L: L[i], wR: wR[i], wL: wL[i] });
    return { frames, belt, seg, tilt, T, flightDrop, flightFraction: flight / N, stanceFraction: fv.filter((v) => v > 0.5).length / N };
  }

  // ---------------------------------------------------------------- masses
  function massModel(design, configKey) {
    const cfg = design.configs[configKey], mods = cfg.modules;
    const items = [{ module: 'core', name: 'Batería ' + design.batteryPack.label, mass: design.batteryPack.mass, loc: 'waist', qty: cfg.packs }];
    for (const s of design.structure) if (mods.includes(s.module)) items.push(Object.assign({}, s));
    for (const j of ['hip', 'knee', 'ankle']) {
      if (!mods.includes(j)) continue;
      const a = ACTUATORS[design.joints[j].actuator], m = design.actuatorMount[j];
      items.push({ module: j, name: 'Actuador ' + a.name, mass: a.mass, loc: m.loc, d: m.d, qty: 2, actuator: true });
    }
    const byLoc = { waist: 0, thigh: 0, shank: 0, foot: 0 };
    let total = 0;
    for (const it of items) { byLoc[it.loc] += it.mass * it.qty; total += it.mass * it.qty; }
    const perLeg = (loc) => items.filter((it) => it.loc === loc).map((it) => ({ m: it.mass, d: it.d === undefined ? 0 : it.d }));
    return { items, byLoc, total, thigh: perLeg('thigh'), shank: perLeg('shank'), foot: perLeg('foot'), modules: mods, batteryWh: cfg.packs * design.batteryPack.wh };
  }

  // ---------------------------------------------------------------- simulate
  function simulate(norm, gaitKey, opts) {
    const o = Object.assign({ bodyMass: 75, height: 1.75, payload: 0, config: 'full', assist: 0.3, selfCarry: 1, tiltOffset: 0, design: DESIGN }, opts || {});
    const design = o.design, gait = norm.gaits[gaitKey], c = gait.curves, T = gait.stride_time;
    const assist = typeof o.assist === 'number' ? { hip: o.assist, knee: o.assist, ankle: o.assist } : o.assist;
    const kin = kinematics(gait, o.height, o.tiltOffset);
    const mm = massModel(design, o.config);
    const mb = o.bodyMass, mExo = mm.total, mAdd = mExo + o.payload;

    const q = { hip: c.hip_ang.mean.map((v) => v * DEG), knee: c.knee_ang.mean.map((v) => v * DEG), ankle: c.ankle_ang.mean.map((v) => v * DEG) };
    // joint velocity in the direction of positive (extensor / plantarflexor) moment
    const w = { hip: deriv(q.hip, T).map((v) => -v), knee: deriv(q.knee, T).map((v) => -v), ankle: deriv(q.ankle, T).map((v) => -v) };
    const acc = { hip: deriv(w.hip, T), knee: deriv(w.knee, T), ankle: deriv(w.ankle, T) };
    const bio = { hip: c.hip_mom.mean, knee: c.knee_mom.mean, ankle: c.ankle_mom.mean }; // Nm/kg
    const fv = c.grf_v.mean, fa = c.grf_ap.mean;
    const stance = fv.map((v) => smooth01(v / 2));
    // specific force at the pelvis (a - g): both legs' GRF per kg of body
    const fx = fa.map((v, i) => v + fa[(i + N / 2) % N]), fy = fv.map((v, i) => v + fv[(i + N / 2) % N]);

    // --- swing-phase moments needed to carry the exo's own leg masses
    const pts = [];
    for (const p of mm.thigh) pts.push({ m: p.m, seg: 'thigh', pos: (f) => [f.knee[0] * p.d, f.knee[1] * p.d] });
    for (const p of mm.shank) pts.push({ m: p.m, seg: 'shank', pos: (f) => [f.knee[0] + (f.ankle[0] - f.knee[0]) * p.d, f.knee[1] + (f.ankle[1] - f.knee[1]) * p.d] });
    for (const p of mm.foot) pts.push({ m: p.m, seg: 'foot', pos: (f) => [0.5 * (f.ankle[0] + f.ball[0]), 0.5 * (f.ankle[1] + f.heel[1])] });
    const swing = { hip: new Array(N).fill(0), knee: new Array(N).fill(0), ankle: new Array(N).fill(0) };
    for (const p of pts) {
      const X = kin.frames.map((f) => p.pos(f.R)[0]), Y = kin.frames.map((f) => p.pos(f.R)[1]);
      const ax = deriv(deriv(X, T, 12), T, 12), ay = deriv(deriv(Y, T, 12), T, 12);
      for (let i = 0; i < N; i++) {
        const f = kin.frames[i].R, Fx = p.m * (ax[i] + fx[i]), Fy = p.m * (ay[i] + fy[i]);
        const z = (ox, oy) => (X[i] - ox) * Fy - (Y[i] - oy) * Fx; // +z = flexion torque at hip
        swing.hip[i] += -z(0, 0);
        if (p.seg !== 'thigh') swing.knee[i] += z(f.knee[0], f.knee[1]);
        if (p.seg === 'foot') swing.ankle[i] += -z(f.ankle[0], f.ankle[1]);
      }
    }

    const joints = {}, active = ['hip', 'knee', 'ankle'].filter((j) => mm.modules.includes(j));
    let pBat = design.housekeepingW, posExo = 0, negExo = 0, posSelf = 0;
    for (const j of ['hip', 'knee', 'ankle']) {
      const base = bio[j].map((m, i) => m * (mb + stance[i] * o.payload)); // no exo, same payload
      const req = bio[j].map((m, i) => m * (mb + stance[i] * mAdd) + (1 - stance[i]) * swing[j][i]);
      const J = { angle: q[j].map((v) => v / DEG), omega: w[j], base, req, exo: new Array(N).fill(0), human: req.slice(), active: active.includes(j) };
      if (J.active) {
        const jd = design.joints[j], act = ACTUATORS[jd.actuator], r = jd.ratio;
        const Jref = act.rotorInertia * act.gear * act.gear;
        const pe = new Array(N), ta = new Array(N);
        let sat = 0, over = 0, wanted = 0, given = 0;
        for (let i = 0; i < N; i++) {
          // carry the device's own weight and inertia, then take a share of the wearer's moment
          let cmd = o.selfCarry * (req[i] - base[i]) + assist[j] * base[i];
          if (!jd.bidirectional && cmd < 0) cmd = 0;
          const wa = w[j][i] * r; // actuator output speed
          // torque the actuator spends on itself (rotor inertia + friction), compensated by the controller
          const self = Jref * acc[j][i] * r + act.coulomb * Math.tanh(wa / 0.3) + act.viscous * wa;
          let tAct = cmd / r + self;
          const lim = torqueLimit(act, wa, tAct * wa > 0);
          if (Math.abs(wa) > act.wNoLoad) over++;
          if (Math.abs(tAct) > lim) { tAct = Math.sign(tAct) * lim; sat++; }
          let del = (tAct - self) * r;
          if (Math.sign(del) !== Math.sign(cmd) || cmd === 0) del = 0; // never push against the wearer
          if (!jd.bidirectional && del < 0) del = 0;
          J.exo[i] = del; J.human[i] = req[i] - del; ta[i] = tAct;
          wanted += Math.abs(cmd); given += Math.abs(del);
          const pm = tAct * wa; // mechanical power at the actuator output
          const pIn = pm >= 0 ? pm / design.gearEff : pm * design.gearEff;
          const tm = pm >= 0 ? tAct / design.gearEff : tAct * design.gearEff;
          const p = pIn + (tm / act.km) * (tm / act.km);
          pe[i] = (p >= 0 ? p / design.inverterEff : p * design.regenEff) + design.idleW;
          const pj = del * w[j][i];
          if (pj > 0) posExo += pj / N; else negExo += -pj / N;
          // share of that power spent moving the device itself rather than helping the wearer
          const selfShare = cmd !== 0 ? Math.max(0, Math.min(1, o.selfCarry * (req[i] - base[i]) / cmd)) : 0;
          if (pj > 0) posSelf += selfShare * pj / N;
        }
        J.actuator = act.name; J.ratio = r;
        J.actTorque = ta; J.elec = pe;
        J.peakTorque = maxAbs(J.exo); J.rmsAct = rms(ta); J.peakAct = maxAbs(ta);
        J.peakSpeed = maxAbs(w[j]) * r; // rad/s at actuator output
        J.thermal = J.rmsAct / act.tauRated; J.torqueUse = J.peakAct / act.tauPeak; J.speedUse = J.peakSpeed / act.wNoLoad;
        J.saturated = sat / N; J.overspeed = over / N; J.delivered = wanted > 0 ? given / wanted : 1;
        J.elecAvg = mean(pe); pBat += 2 * J.elecAvg;
      }
      J.power = J.exo.map((t, i) => t * w[j][i]);
      J.peakOmega = maxAbs(w[j]);
      joints[j] = J;
    }
    posExo *= 2; negExo *= 2; posSelf *= 2; // both legs

    // --- metabolic first-order estimate
    const netRate = gaitKey === 'walk' ? METAB.netWalk : METAB.runCot * gait.speed; // W/kg
    const scale = netRate / METAB.netWalk;
    let massPenalty = 0;
    for (const loc of Object.keys(mm.byLoc)) massPenalty += METAB.betaWalk[loc] * scale * mm.byLoc[loc];
    const pDis = negExo > posExo ? posExo - negExo : 0;
    // Power that only moves the device can at best cancel the cost of carrying it.
    const selfGain = Math.min(massPenalty, posSelf / METAB.eta);
    const gain = selfGain + Math.max(0, posExo - posSelf + pDis) / METAB.eta;
    const baseline = netRate * (mb + o.payload);
    const usableWh = mm.batteryWh * design.batteryPack.usable;

    // --- joint-level relief (mechanical, no physiology assumed)
    const relief = {};
    for (const j of ['hip', 'knee', 'ankle']) {
      const b = rms(joints[j].base), h = rms(joints[j].human);
      relief[j] = 1 - h / b;
    }

    return {
      gait: gaitKey, speed: gait.speed, strideTime: T, config: o.config, kin, mass: mm, joints,
      opts: { bodyMass: mb, height: o.height, payload: o.payload, assist },
      power: { battery: pBat, exoPositive: posExo, exoNegative: negExo, exoSelf: posSelf },
      endurance: { hours: usableWh / pBat, km: usableWh / pBat * gait.speed * 3.6, usableWh },
      metabolic: {
        baselineW: baseline, massPenaltyW: massPenalty, assistGainW: gain,
        netChangeW: massPenalty - gain, netChangePct: (massPenalty - gain) / baseline,
        offPct: massPenalty / baseline,
      },
      relief,
    };
  }

  return { ACTUATORS, DESIGN, METAB, N, G, simulate, kinematics, massModel, torqueLimit, deriv, anthropometry, legFK };
});
