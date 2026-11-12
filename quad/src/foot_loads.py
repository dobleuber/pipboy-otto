"""Peak forces on a foot in simulation: the gaits, the wave and drops onto the floor.

    cad run src/foot_loads.py
"""
import math
import mujoco, numpy as np
import params as p
from walk_sim import load, targets, BASELINE, CTRL_DT, SETTLE, RISE

def run(gait, duration=6.0, drop_mm=0.0):
    m, stall, noload = load()
    d = mujoco.MjData(m); mujoco.mj_resetData(m, d)
    d.qpos[2] += drop_mm / 1000
    mujoco.mj_forward(m, d)
    z0 = d.qpos[2]
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, a) for a in range(m.nu)]
    feet = {g: mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g]) for g in range(m.ngeom)
            if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith("foot_collision")}
    peak, f6 = 0.0, np.zeros(6)
    side = fore = 0.0
    forces = []
    for i in range(round(duration / m.opt.timestep)):
        t = i * m.opt.timestep
        if i % 20 == 0:
            q = targets(t, gait) if not drop_mm else {k: 0.0 for k in names}
            d.ctrl[:] = np.radians([q[n] for n in names])
        mujoco.mj_step(m, d)
        for c in range(d.ncon):
            con = d.contact[c]
            g = con.geom1 if con.geom1 in feet else con.geom2 if con.geom2 in feet else None
            if g is not None:
                mujoco.mj_contactForce(m, d, c, f6)
                n = f6[0]
                world = con.frame.reshape(3, 3).T @ f6[:3]      # contact force in the world
                side, fore = max(side, abs(world[1])), max(fore, abs(world[0]))
                peak = max(peak, n)
                if t > SETTLE + RISE + 1 or drop_mm: forces.append(n)
    if drop_mm: print('   fell', round(1000 * (z0 - d.qpos[2]), 1), 'mm; contacts at end', d.ncon)
    return peak, (np.percentile(forces, 99) if forces else 0), m.body_mass.sum() * 9.81, side, fore

for label, gait, kw in (("trot, default", dict(BASELINE), {}), ("trot, high step", {**BASELINE, "lift": 8.0}, {}),
                        ("trot 4 Hz, 36 mm", {**BASELINE, "freq": 4.0, "step": 36.0}, {}),
                        ("crawl", {**BASELINE, "gait": "crawl", "freq": 1.0, "step": 16.0, "lift": 8.0, "duty": 0.75}, {}),
                        ("wave", {"gait": "wave", "height": 46.0, **{k: BASELINE[k] for k in ("freq", "step", "lift", "duty", "x0", "turn", "sway")}}, {"duration": 7.0}),
                        ("drop from 20 mm", dict(BASELINE), {"drop_mm": 20, "duration": 1.0}),
                        ("drop from 50 mm", dict(BASELINE), {"drop_mm": 50, "duration": 1.0}),
                        ("drop from 100 mm", dict(BASELINE), {"drop_mm": 100, "duration": 1.0})):
    peak, p99, weight, side, fore = run(gait, **kw)
    print(f"{label:<20} peak foot force {peak:5.2f} N ({peak / weight:4.1f} x weight)   99th pct {p99:5.2f} N   weight {weight:.3f} N   side {side:5.2f} N  fore-aft {fore:5.2f} N")
