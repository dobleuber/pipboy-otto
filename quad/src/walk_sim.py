# /// script
# dependencies = ["glfw", "pyopengl"]
# ///
"""Walking tests of the mini quadruped in MuJoCo: an open-loop trot on position servos.

    cad run src/walk_sim.py                      # the baseline walk, numbers only
    cad run src/walk_sim.py --suite              # every test -> results/results.json and results/RESULTS.md
    xvfb-run -a env MUJOCO_GL=glfw cad run src/walk_sim.py --video media/trot.mp4

The servo is modelled as a position loop (full torque at ~4 deg of error) clamped to its stall torque,
with a damping that takes the torque to zero at the no-load speed, and targets refreshed at 50 Hz like
a real PWM servo. No feedback from the body: what the firmware would do with nothing but a timer.
"""
import argparse
import json
import math
import os
import subprocess

import mujoco
import numpy as np

import params as p
from gait import crawl, stand, trot

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCENE = os.path.join(ROOT, "sim", "scene.xml")
CTRL_DT = 0.02          # s: one servo PWM frame (50 Hz)
SETTLE, RISE = 0.4, 0.6  # s: hold as built, then move to the walking height
FLOOR_Z = -0.0538        # the scene's floor (sim/scene.xml)
BASELINE = dict(gait="trot", freq=2.0, step=20.0, lift=8.0, height=46.0, duty=0.5, x0=0.0, turn=0.0, sway=10.0)
CRAWL = dict(gait="crawl", freq=1.0, step=16.0, lift=8.0, duty=0.75)


def load(stall=None, noload=None, friction=None, payload_g=0.0, kp=None, slope_deg=0.0, step_mm=0.0):
    """The scene's model, with the servo, the floor, the load or the terrain changed for a test.

    slope_deg > 0 is uphill (gravity tilted, the same as an incline); step_mm is a step up 120 mm ahead.
    """
    if step_mm:
        spec = mujoco.MjSpec.from_file(SCENE)
        h = step_mm / 1000
        spec.worldbody.add_geom(name="step", type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.5, 0.5, h / 2],
                                pos=[0.12 + 0.5, 0, FLOOR_Z + h / 2], friction=[0.8, 0.005, 0.0001],
                                rgba=[0.75, 0.6, 0.4, 1])
        m = spec.compile()
    else:
        m = mujoco.MjModel.from_xml_path(SCENE)
    if slope_deg:
        a = math.radians(slope_deg)
        m.opt.gravity[:] = [-9.81 * math.sin(a), 0, -9.81 * math.cos(a)]
    stall0 = p.SERVO_STALL_NM
    stall = stall0 if stall is None else stall
    noload = p.SERVO_NOLOAD_RAD_S if noload is None else noload
    for a in range(m.nu):
        j = m.actuator_trnid[a, 0]
        m.jnt_actfrcrange[j] = [-stall, stall]
        m.dof_damping[m.jnt_dofadr[j]] = stall / noload
        if kp is not None:
            m.actuator_gainprm[a, 0] = kp
            m.actuator_biasprm[a, 1] = -kp
    if friction is not None:
        for g in range(m.ngeom):
            name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or ""
            if name in ("floor", "step") or name.startswith("foot_collision"):
                m.geom_friction[g, 0] = friction
    if payload_g:
        m.body_mass[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "chassis")] += payload_g / 1000
    m.opt.timestep = 0.001
    return m, stall, noload


def targets(t, gait):
    """Joint targets in degrees at time t: as built, rise to the walking height, then trot."""
    if t < SETTLE:
        return {k: 0.0 for k in stand()}
    pose = stand(height=gait["height"], x0=gait["x0"])
    if t < SETTLE + RISE:
        s = (t - SETTLE) / RISE
        s = 3 * s * s - 2 * s * s * s
        return {k: v * s for k, v in pose.items()}
    kw = {k: v for k, v in gait.items() if k != "gait"}
    return (crawl if gait["gait"] == "crawl" else trot)(t - SETTLE - RISE, **kw)


def euler(q):
    w, x, y, z = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1, min(1, 2 * (w * y - z * x))))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return roll, pitch, yaw


def run(m, stall, noload, gait=None, duration=8.0, push=None, video=None, fps=30):
    """Simulate `duration` seconds. Returns the test's numbers; `push` = (time s, force N along +Y, for 0.1 s)."""
    gait = {**BASELINE, **(gait or {})}
    d = mujoco.MjData(m)
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, a) for a in range(m.nu)]
    dofs = [m.jnt_dofadr[m.actuator_trnid[a, 0]] for a in range(m.nu)]
    qadr = [m.jnt_qposadr[m.actuator_trnid[a, 0]] for a in range(m.nu)]
    chassis = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    floor_z = m.geom_pos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "floor"), 2]
    steps_per_frame = round(CTRL_DT / m.opt.timestep)
    n = round(duration / m.opt.timestep)

    renderer = cam = pipe = None
    if video:
        renderer = mujoco.Renderer(m, 480, 640)
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        cam.trackbodyid = chassis
        cam.distance, cam.azimuth, cam.elevation = 0.27, 125, -16
        cam.lookat[:] = [0, 0, -0.02]
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 0
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = 0
        os.makedirs(os.path.dirname(os.path.abspath(video)), exist_ok=True)
        pipe = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "640x480",
             "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-crf", "20", video], stdin=subprocess.PIPE)
    every = round(1 / fps / m.opt.timestep)

    log = {k: [] for k in ("t", "x", "y", "z", "roll", "pitch", "yaw", "tau", "vel", "err")}
    fell = None
    target = np.zeros(m.nu)
    for i in range(n):
        t = i * m.opt.timestep
        if i % steps_per_frame == 0:
            q = targets(t, gait)
            target = np.radians([q[name] for name in names])
            d.ctrl[:] = target
        d.xfrc_applied[chassis, :] = 0
        if push and push[0] <= t < push[0] + 0.1:
            d.xfrc_applied[chassis, 1] = push[1]
        mujoco.mj_step(m, d)
        roll, pitch, yaw = euler(d.qpos[3:7])
        log["t"].append(t)
        log["x"].append(d.qpos[0]); log["y"].append(d.qpos[1]); log["z"].append(d.qpos[2] - floor_z)
        log["roll"].append(roll); log["pitch"].append(pitch); log["yaw"].append(yaw)
        log["tau"].append(d.qfrc_actuator[dofs].copy())
        log["vel"].append(d.qvel[dofs].copy())
        log["err"].append(target - d.qpos[qadr])
        if fell is None and (abs(roll) > math.radians(50) or abs(pitch) > math.radians(50) or d.qpos[2] - floor_z < 0.025):
            fell = t
        if pipe and i % every == 0:
            renderer.update_scene(d, cam)
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 0
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = 0
            pipe.stdin.write(renderer.render().tobytes())
    if pipe:
        pipe.stdin.close()
        pipe.wait()

    a = {k: np.array(v) for k, v in log.items()}
    t0 = SETTLE + RISE + 1.0                       # steady walking: a second after the trot starts
    w = a["t"] >= t0
    span = a["t"][w][-1] - a["t"][w][0]
    dx, dy = a["x"][w][-1] - a["x"][w][0], a["y"][w][-1] - a["y"][w][0]
    yaw = np.unwrap(a["yaw"])
    k = round(0.5 / m.opt.timestep)                                     # path length on 0.5 s samples
    path = np.hypot(np.diff(a["x"][w][::k]), np.diff(a["y"][w][::k])).sum()
    tau = np.abs(a["tau"][w]) / stall                                  # the loop's command (PWM duty)
    load = np.abs(a["tau"][w] - (stall / noload) * a["vel"][w]) / stall   # torque delivered at the horn (motor current)
    ideal = gait["step"] / 1000 * gait["freq"] / gait["duty"]         # stance sweeps `step` in duty/freq seconds
    return {
        "fell_at_s": fell,
        "speed_mm_s": 1000 * dx / span,
        "path_speed_mm_s": 1000 * path / span,
        "sideways_mm": 1000 * dy,
        "climbed_mm": 1000 * (a["z"][w][-1] - a["z"][w][0]),
        "ideal_speed_mm_s": 1000 * ideal,
        "slip_pct": 100 * (1 - (dx / span) / ideal) if ideal else None,
        "drift_mm_per_m": 1000 * dy / dx if abs(dx) > 1e-3 else None,
        "yaw_rate_deg_s": math.degrees((yaw[w][-1] - yaw[w][0]) / span),
        "roll_max_deg": math.degrees(np.abs(a["roll"][w]).max()),
        "pitch_max_deg": math.degrees(np.abs(a["pitch"][w]).max()),
        "height_min_mm": 1000 * a["z"][w].min(),
        "height_mean_mm": 1000 * a["z"][w].mean(),
        "torque_peak_pct": 100 * tau.max(),
        "torque_rms_pct": 100 * math.sqrt((tau ** 2).mean()),
        "saturated_pct": 100 * (tau > 0.98).mean(),
        "load_rms_pct": 100 * math.sqrt((load ** 2).mean()),
        "load_peak_pct": 100 * load.max(),
        "joint_speed_peak_pct": 100 * np.abs(a["vel"][w]).max() / noload,
        "tracking_rms_deg": math.degrees(math.sqrt((a["err"][w] ** 2).mean())),
        "mass_g": 1000 * m.body_mass.sum(),
        "gait": gait,
    }


def verdict(r):
    """fell / no advance / walks, by what the body did."""
    if r["fell_at_s"] is not None:
        return f"fell at {r['fell_at_s']:.1f} s"
    if r.get("step_mm"):
        return "climbs" if r["climbed_mm"] > 0.9 * r["step_mm"] and r["speed_mm_s"] > 0.4 * r["ideal_speed_mm_s"] else "stuck at the step"
    if r["gait"]["turn"]:
        return "turns" if abs(r["yaw_rate_deg_s"]) > 5 else "no turn"
    return "walks" if r["speed_mm_s"] > 0.4 * r["ideal_speed_mm_s"] else "no advance"


def line(label, r):
    fell = verdict(r)
    return (f"{label:<38} {fell:<18} v {r['speed_mm_s']:6.1f} mm/s (slip {r['slip_pct']:5.1f} %)  "
            f"roll {r['roll_max_deg']:4.1f}  pitch {r['pitch_max_deg']:4.1f} deg  "
            f"cmd rms {r['torque_rms_pct']:4.1f} % sat {r['saturated_pct']:4.1f} %  load rms {r['load_rms_pct']:4.1f} % peak {r['load_peak_pct']:5.1f} %  "
            f"yaw {r['yaw_rate_deg_s']:5.1f} deg/s  side {r['sideways_mm']:6.1f} mm  climbed {r['climbed_mm']:5.1f} mm")


def suite():
    kgcm = 0.0980665
    tests = [("baseline (0.5 kg*cm, 2 Hz, 20 mm)", {}, {}, {})]
    for freq in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for step in (12.0, 20.0, 28.0, 36.0):
            tests.append((f"gait f={freq} Hz step={step:.0f} mm", {}, {"freq": freq, "step": step}, {}))
    for lift in (4.0, 12.0):
        tests.append((f"gait lift={lift:.0f} mm", {}, {"lift": lift}, {}))
    for height in (40.0, 52.0):
        tests.append((f"gait height={height:.0f} mm", {}, {"height": height}, {}))
    for mu in (0.2, 0.3, 0.5, 1.2):
        tests.append((f"friction {mu}", {"friction": mu}, {}, {}))
    for grams in (15, 30, 60):
        tests.append((f"payload +{grams} g", {"payload_g": grams}, {}, {}))
    tests.append(("servo 0.3 kg*cm, 0.15 s/60deg", {"stall": 0.3 * kgcm, "noload": math.radians(60) / 0.15}, {}, {}))
    tests.append(("servo 0.8 kg*cm, 0.09 s/60deg", {"stall": 0.8 * kgcm, "noload": math.radians(60) / 0.09}, {}, {}))
    tests.append(("soft servo loop (kp / 2)", {"kp": 0.35}, {}, {}))
    for k in (0.2, 0.15, 0.1):
        tests.append((f"servo {k} kg*cm, 0.15 s/60deg", {"stall": k * kgcm, "noload": math.radians(60) / 0.15}, {}, {}))
    for grams in (120, 200, 300):
        tests.append((f"payload +{grams} g", {"payload_g": grams}, {}, {}))
    for deg in (5, 10, 15, 20, -10, -20):
        tests.append((f"slope {deg:+d} deg", {"slope_deg": deg}, {}, {}))
    for deg in (10, 15, 20):   # leaning into the slope: feet set back by height * tan(slope)
        tests.append((f"slope {deg:+d} deg, leaning", {"slope_deg": deg},
                      {"x0": -50.0 * math.tan(math.radians(deg))}, {}))
    tests.append(("crawl (1 Hz, 16 mm)", {}, dict(CRAWL), {}))
    tests.append(("crawl, no sway", {}, {**CRAWL, "sway": 0.0}, {}))
    tests.append(("crawl 1.5 Hz, 24 mm", {}, {**CRAWL, "freq": 1.5, "step": 24.0}, {}))
    for deg in (10, 15, 20):
        tests.append((f"crawl, slope {deg:+d} deg, leaning", {"slope_deg": deg},
                      {**CRAWL, "x0": -50.0 * math.tan(math.radians(deg))}, {}))
    tests.append(("crawl, step up 6 mm (16 s)", {"step_mm": 6}, dict(CRAWL), {"duration": 16.0}))
    tests.append(("crawl, friction 0.3", {"friction": 0.3}, dict(CRAWL), {}))
    tests.append(("PLANTED: servo 0.03 kg*cm (must fail)", {"stall": 0.03 * kgcm, "noload": math.radians(60) / 0.15}, {}, {}))
    for mm in (2, 4, 6, 8, 10):
        tests.append((f"step up {mm} mm", {"step_mm": mm}, {}, {}))
    for mm in (6, 10):
        tests.append((f"step up {mm} mm, lift 14 mm", {"step_mm": mm}, {"lift": 14.0}, {}))
    for turn in (0.5, 1.0):
        tests.append((f"turn {turn}", {}, {"turn": turn}, {}))
    for force in (0.4, 1.0, 2.0, 4.0):
        tests.append((f"side push {force} N for 0.1 s", {}, {}, {"push": (4.0, force)}))
    results = []
    for label, model_kw, gait_kw, run_kw in tests:
        m, stall, noload = load(**model_kw)
        r = run(m, stall, noload, gait=gait_kw, **run_kw)
        r.update(label=label, model=model_kw, push=run_kw.get("push"), step_mm=model_kw.get("step_mm"))
        r["verdict"] = verdict(r)
        results.append(r)
        print(line(label, r), flush=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    with open(os.path.join(ROOT, "results", "RESULTS.md"), "w") as f:
        f.write("# Walking tests (generated by `cad run src/walk_sim.py --suite`)\n\n")
        f.write("8 s each, numbers over the steady part. Load = torque delivered at the horn, as % of the servo's stall torque in that test; command saturated = share of time the position loop asks for full torque.\n\n")
        f.write("| test | result | speed mm/s | slip % | roll max ° | pitch max ° | load rms % | load peak % | command saturated % | yaw °/s |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            fell = r["verdict"]
            f.write(f"| {r['label']} | {fell} | {r['speed_mm_s']:.0f} | {r['slip_pct']:.0f} | {r['roll_max_deg']:.1f} | "
                    f"{r['pitch_max_deg']:.1f} | {r['load_rms_pct']:.0f} | {r['load_peak_pct']:.0f} | "
                    f"{r['saturated_pct']:.1f} | {r['yaw_rate_deg_s']:.1f} |\n")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--duration", type=float, default=8.0)
    ap.add_argument("--gait", choices=("trot", "crawl"), default="trot")
    ap.add_argument("--slope", type=float, default=0.0)
    ap.add_argument("--step-up", type=float, default=0.0, help="a step up, mm")
    for k, v in BASELINE.items():
        if k != "gait":
            ap.add_argument(f"--{k}", type=float, default=None)
    args = ap.parse_args()
    if args.suite:
        suite()
    else:
        m, stall, noload = load(slope_deg=args.slope, step_mm=args.step_up)
        gait = dict(CRAWL) if args.gait == "crawl" else {}
        gait.update({k: getattr(args, k) for k in BASELINE if k != "gait" and getattr(args, k) is not None})
        r = run(m, stall, noload, gait=gait, duration=args.duration, video=args.video)
        r["step_mm"] = args.step_up
        print(line(args.gait, r))
        print(json.dumps(r, indent=1))
