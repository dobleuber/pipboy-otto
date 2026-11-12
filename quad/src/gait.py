"""Leg inverse kinematics and a trot, shared by the CAD model's motion and the simulation.

Every joint turns about world +Y; q = 0 is the as-built stance (the servo's centre).
Pure Python: no CAD kernel, no MuJoCo.
"""
import math

from params import FOOT_R, HIP_X, L1, L2, LEGS, SERVO_TRAVEL, STANCE

NOMINAL_H = (L1 + L2) * math.cos(math.radians(STANCE))   # hip axis above the foot centre, as built


def leg_ik(sx, x, z):
    """Joint angles (hip, knee) in degrees that put the foot centre at (x, z) from the hip axis.

    x forward, z up (negative below the hip). sx = +1 front leg (knee back), -1 rear (knee forward).
    """
    d = math.hypot(x, z)
    d = min(max(d, abs(L1 - L2) + 1e-6), L1 + L2 - 1e-6)
    gamma = math.atan2(-x, -z)                      # foot direction, as a turn about +Y from straight down
    phi = math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))
    psi = math.acos((L2 * L2 + d * d - L1 * L1) / (2 * L2 * d))
    alpha = gamma + sx * phi                        # thigh
    beta = gamma - sx * psi                         # shank
    a0, b0 = sx * math.radians(STANCE), -sx * math.radians(STANCE)
    hip = alpha - a0
    knee = (beta - alpha) - (b0 - a0)
    return math.degrees(hip), math.degrees(knee)


def foot_offset(phase, step, lift, duty):
    """Foot (dx, dz) from its neutral point at a phase in [0, 1): stance first, then swing."""
    if phase < duty:                                # stance: the foot goes back at constant speed
        s = phase / duty
        return step * (0.5 - s), 0.0
    s = (phase - duty) / (1 - duty)                 # swing: forward on a cycloid, lifted on a sine arch
    dx = step * ((s - math.sin(2 * math.pi * s) / (2 * math.pi)) - 0.5)
    return dx, lift * math.sin(math.pi * s)


TROT = {"fl": 0.0, "rr": 0.0, "fr": 0.5, "rl": 0.5}      # diagonal pairs together


def trot(t, *, freq=2.0, step=20.0, lift=5.0, height=46.0, duty=0.5, x0=0.0, ramp=0.5, turn=0.0, **_):
    """Joint targets {joint: degrees} at time t (s). step, lift, height in mm; freq in Hz.

    The stride grows from 0 over `ramp` seconds. `turn` in [-1, 1] shortens one side's stride.
    """
    gain = min(1.0, t / ramp) if ramp > 0 else 1.0
    q = {}
    for name, (sx, sy) in LEGS.items():
        side = 1.0 - turn * sy
        dx, dz = foot_offset((t * freq + TROT[name]) % 1.0, step * gain * side, lift * gain, duty)
        hip, knee = leg_ik(sx, x0 + dx, -height + dz)
        q[f"hip_{name}"], q[f"knee_{name}"] = hip, knee
    return q


CRAWL = {"rl": 0.75, "fl": 0.5, "rr": 0.25, "fr": 0.0}   # one foot in the air at a time: RL, FL, RR, FR


def crawl(t, *, freq=1.0, step=16.0, lift=8.0, height=46.0, sway=10.0, x0=0.0, ramp=0.5, turn=0.0, **_):
    """A statically stable walk: three feet down, the body swayed fore and aft over the support triangle.

    The legs have no sideways joint, so the weight is shifted along X only: forward while a rear foot is
    in the air, back while a front one is (`sway` mm each way).
    """
    gain = min(1.0, t / ramp) if ramp > 0 else 1.0
    cycle = t * freq
    shift = sway * gain * math.sin(4 * math.pi * cycle)        # + = body forward = feet back
    q = {}
    for name, (sx, sy) in LEGS.items():
        side = 1.0 - turn * sy
        dx, dz = foot_offset((cycle + CRAWL[name]) % 1.0, step * gain * side, lift * gain, 0.75)
        hip, knee = leg_ik(sx, x0 - shift + dx, -height + dz)
        q[f"hip_{name}"], q[f"knee_{name}"] = hip, knee
    return q


def smooth(s):
    s = min(1.0, max(0.0, s))
    return 3 * s * s - 2 * s * s * s


def wave(t, *, height=46.0, lean=12.0, **_):
    """Say hello: sit back on three legs, lift the front-left leg and wave it, then stand again (5 s).

    The body leans back (`lean` mm) and drops its rear first, so the weight is over the three feet that stay.
    """
    sit = smooth(t / 1.0) * smooth((5.0 - t) / 1.0)           # 0 standing, 1 sitting back
    up = smooth((t - 1.0) / 0.5) * smooth((4.0 - t) / 0.5)     # 0 paw on the floor, 1 paw in the air
    q = {}
    for name, (sx, sy) in LEGS.items():
        h = height + (3.0 if sx > 0 else -6.0) * sit          # front up a little, rear down: a sitting dog
        x, z = lean * sit, -h
        if name == "fl":
            x, z = x + (28.0 - x) * up, z + (-34.0 - z) * up   # the paw forward and up, as far as a 90 deg knee lets it
        hip, knee = leg_ik(sx, x, z)
        if name == "fl":
            knee += 22.0 * up * math.sin(2 * math.pi * 2.5 * (t - 1.5))
        q[f"hip_{name}"], q[f"knee_{name}"] = hip, knee
    return q


def dance(t, *, height=44.0, beat=1.5, **_):
    """A wiggle with all four feet on the floor: bob, rock fore and aft, and roll the shoulders (6 s)."""
    gain = smooth(t / 0.6) * smooth((6.0 - t) / 0.6)
    w = 2 * math.pi * beat * t
    q = {}
    for name, (sx, sy) in LEGS.items():
        h = height + gain * (3.0 * math.sin(2 * w)            # bob, twice a beat
                             + 5.0 * sx * math.sin(w)         # nod: front and rear in turn
                             + 4.0 * sy * math.sin(w + math.pi / 2))   # roll: left and right in turn
        x = gain * 6.0 * math.cos(w)                          # and a slide fore and aft
        q[f"hip_{name}"], q[f"knee_{name}"] = leg_ik(sx, x, -h)
    return q


def stand(height=46.0, x0=0.0):
    q = {}
    for name, (sx, sy) in LEGS.items():
        q[f"hip_{name}"], q[f"knee_{name}"] = leg_ik(sx, x0, -height)
    return q


def leg_points(sx, hip, knee):
    """Knee and foot (x, z) in the body's frame for a leg's joint angles in degrees."""
    a = math.radians(sx * STANCE + hip)
    b = a + math.radians(-2 * sx * STANCE + knee)
    kx, kz = sx * HIP_X - L1 * math.sin(a), -L1 * math.cos(a)
    return (kx, kz), (kx - L2 * math.sin(b), kz - L2 * math.cos(b))


def _segment_gap(a0, a1, b0, b1):
    """Shortest distance between two segments in the plane."""
    def point_seg(pt, s0, s1):
        dx, dz = s1[0] - s0[0], s1[1] - s0[1]
        k = ((pt[0] - s0[0]) * dx + (pt[1] - s0[1]) * dz) / (dx * dx + dz * dz or 1e-12)
        k = min(1.0, max(0.0, k))
        return math.hypot(pt[0] - s0[0] - k * dx, pt[1] - s0[1] - k * dz)

    def cross(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])

    if cross(a0, a1, b0) * cross(a0, a1, b1) < 0 and cross(b0, b1, a0) * cross(b0, b1, a1) < 0:
        return 0.0
    return min(point_seg(a0, b0, b1), point_seg(a1, b0, b1), point_seg(b0, a0, a1), point_seg(b1, a0, a1))


THIGH_TAIL = 4.9       # mm: the centre of the thigh plate's round end, past the knee axis (the plate ends 11.4 past)
THIGH_HALF = 6.5       # half width of the thigh's plate
SHANK_HALF = 5.6       # the lower leg's widest half width (its knee boss)
MARGIN = 1.5


def legs_clear(q):
    """True if no front leg can touch the rear leg of its side at these joint angles (degrees).

    The two legs of a side swing in the same planes, so they can meet when both reach inward. Each thigh
    (with its knee servo) and each lower leg is taken as a rounded bar in the side view; bars of the two
    legs must stay MARGIN apart. check_guard.py holds it to the CAD's own interference test on 40 random
    poses: it never calls a colliding pose clear (and refuses a few clear ones).
    """
    for side in ("l", "r"):
        bars = {}
        for sx, n in ((1, "f"), (-1, "r")):
            hip = (sx * HIP_X, 0.0)
            knee, foot = leg_points(sx, q[f"hip_{n}{side}"], q[f"knee_{n}{side}"])
            ux, uz = (knee[0] - hip[0]) / L1, (knee[1] - hip[1]) / L1
            tail = (knee[0] + THIGH_TAIL * ux, knee[1] + THIGH_TAIL * uz)
            bars[n] = {"thigh": (hip, tail), "shank": (knee, foot), "foot": foot}
        f, r = bars["f"], bars["r"]
        if _segment_gap(*f["thigh"], *r["thigh"]) < 2 * THIGH_HALF + MARGIN:
            return False
        if _segment_gap(*f["shank"], *r["shank"]) < 2 * SHANK_HALF + MARGIN:
            return False
        for a, b in ((f, r), (r, f)):     # a foot ball against the other leg's knee servo
            if _segment_gap(a["foot"], a["foot"], *b["thigh"]) < FOOT_R + THIGH_HALF + MARGIN:
                return False
    return True


def within_travel(q, travel=SERVO_TRAVEL):
    return all(abs(v) <= travel for v in q.values())


MOVES = {"trot": (trot, 0.5), "crawl": (crawl, 1.0), "wave": (wave, 5.0), "dance": (dance, 6.0)}   # name: (function, seconds)


if __name__ == "__main__":
    # The IK's own check: forward kinematics of what it returns lands on the target, and zero is the stance.
    def fk(sx, hip, knee):
        a = math.radians(sx * STANCE + hip)
        b = a + math.radians(-2 * sx * STANCE + knee)
        return (-L1 * math.sin(a) - L2 * math.sin(b), -L1 * math.cos(a) - L2 * math.cos(b))

    worst = 0.0
    for sx in (1, -1):
        assert max(abs(v) for v in leg_ik(sx, 0, -NOMINAL_H)) < 1e-6
        for x in range(-20, 21, 5):
            for z in range(-56, -29, 2):
                fx, fz = fk(sx, *leg_ik(sx, x, z))
                worst = max(worst, math.hypot(fx - x, fz - z))
    print(f"IK round trip: worst error {worst:.2e} mm; nominal height {NOMINAL_H:.2f} mm")
    for name, (fn, seconds) in MOVES.items():
        t0 = 1.0 if name in ("trot", "crawl") else 0.0          # the gaits: one steady cycle
        qs = [fn(t0 + seconds * i / 400) for i in range(401)]
        lo = {k: min(q[k] for q in qs) for k in qs[0]}
        hi = {k: max(q[k] for q in qs) for k in qs[0]}
        assert all(within_travel(q) for q in qs), f"{name} leaves the servo travel"
        assert all(legs_clear(q) for q in qs), f"{name} brings two legs together"
        print(f"{name}: within +/-{SERVO_TRAVEL:.0f} deg and legs clear; joints "
              + ", ".join(f"{k} {lo[k]:.0f}..{hi[k]:.0f}" for k in ("hip_fl", "knee_fl", "hip_rl", "knee_rl")))
    assert not legs_clear({**stand(), "hip_fl": 30, "hip_rl": -30}), "the guard must refuse a pose known to collide"
    print("guard refuses hips 30 deg inward on one side (collides in CAD)")
