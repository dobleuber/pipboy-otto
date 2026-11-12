"""The stress study's model: one whole leg with its knee locked (README, "¿Aguantan las patas y los servos?").

    cad run src/leg_study.py                     # prints the model's id
    cad model solve <id> --study fea/vertical+out.json --out tmp/fea/out
"""
import math
import build123d as bd
from bd_materials import plastics
from cad import model
import params as p
from parts import FOOT_FLAT, box, horn, leg_line, servo, thigh, zcyl


def lower_leg_faceted():
    """The lower leg for analysis: the same outline as parts.lower_leg, as straight segments (the mesher
    cannot place loads on its spline-edged faces)."""
    t = p.SHANK_T
    xe = p.L2 - FOOT_FLAT - 0.4
    xs = [3.5 + (xe - 3.5) * i / 29 for i in range(30)]
    half = lambda x: 4.3 - 2.6 * (x - 3.5) / (xe - 3.5)
    pts = [(x, leg_line(1, x) - half(x)) for x in xs] + [(x, leg_line(1, x) + half(x)) for x in reversed(xs)]   # anticlockwise
    body = bd.extrude(bd.Circle(5.6) + bd.Polygon(*pts, align=None), t, dir=(0, 0, 1))
    body += box(xe - 1.0, p.L2 + 1.5, -p.PEG / 2, p.PEG / 2, 0, p.PEG)
    body -= [zcyl(0, 0, -1, t + 1, 2.4)] + [zcyl(x, 0, -1, t + 1, 1.2) for x in (6.0, 11.0)]
    body.label = "shank"
    body.material = plastics.pla()
    return body


@model
def leg_study():
    """One whole leg as built, in the thigh's frame, its knee locked: hip horn, thigh, knee servo, knee horn,
    lower leg. The front-left leg: the lower leg stands 70 deg from the thigh."""
    hip_horn = bd.Pos(0, 0, 0) * horn().shape
    hip_horn.label = "hip_horn"
    knee_servo = bd.Pos(p.L1, 0, p.THIGH_T) * servo().shape
    knee_servo.label = "knee_servo"
    at_knee = bd.Pos(p.L1, 0, p.THIGH_T + p.SERVO_H) * bd.Rot(0, 0, -2 * p.STANCE)
    knee_horn = at_knee * horn().shape
    knee_horn.label = "knee_horn"
    shank = at_knee * lower_leg_faceted()
    shank.label = "shank"
    return bd.Compound(children=[hip_horn, thigh().shape, knee_servo, knee_horn, shank], label="leg")


if __name__ == "__main__":
    leg_study()
