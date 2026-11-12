"""Leg inverse kinematics and a trot, shared by the CAD model's motion and the simulation.

Every joint turns about world +Y; q = 0 is the as-built stance (the servo's centre).
Pure Python: no CAD kernel, no MuJoCo.
"""
import math

from params import L1, L2, LEGS, SERVO_TRAVEL, STANCE

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


def trot(t, *, freq=2.0, step=20.0, lift=8.0, height=46.0, duty=0.5, x0=0.0, ramp=0.5, turn=0.0, **_):
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


def stand(height=46.0, x0=0.0):
    q = {}
    for name, (sx, sy) in LEGS.items():
        q[f"hip_{name}"], q[f"knee_{name}"] = leg_ik(sx, x0, -height)
    return q


def within_travel(q, travel=SERVO_TRAVEL):
    return all(abs(v) <= travel for v in q.values())


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
    lo = {k: 1e9 for k in stand()}
    hi = {k: -1e9 for k in stand()}
    for i in range(1000):
        for k, v in trot(1 + i / 1000 * 0.5).items():
            lo[k], hi[k] = min(lo[k], v), max(hi[k], v)
    for k in lo:
        print(f"  {k}: {lo[k]:6.1f} .. {hi[k]:6.1f} deg")
