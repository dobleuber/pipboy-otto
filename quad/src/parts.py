"""The quadruped's parts, each a model in the frame it is used in.

Printed parts are PLA on an FDM printer and are modelled as they print: flat face down, Z up.

Check: cad model dfm "$ID" --process printing --technology fdm --material pla
"""
import build123d as bd
from bd_materials import plastics
from cad import model

import params as p

PRINTED = "#f2a53a"   # orange PLA
DARK = "#30343a"


def box(x0, x1, y0, y1, z0, z1):
    """An axis-aligned box from its corners."""
    lo = (min(x0, x1), min(y0, y1), min(z0, z1))
    size = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    return bd.Pos(lo[0] + size[0] / 2, lo[1] + size[1] / 2, lo[2] + size[2] / 2) * bd.Box(*size)


def zcyl(x, y, z0, z1, d):
    """A cylinder along Z."""
    return bd.Pos(x, y, (z0 + z1) / 2) * bd.Cylinder(d / 2, abs(z1 - z0))


# ----------------------------------------------------------------------------- bought parts


def servo_boxes(grow=0.0):
    """The servo's envelope as boxes (x0, x1, y0, y1, z0, z1) in its own frame, grown by a clearance."""
    w = p.SERVO_W / 2
    x0, x1 = p.SERVO_SHAFT_END - p.SERVO_L, p.SERVO_SHAFT_END
    g = grow
    case = (x0 - g, x1 + g, -w - g, w + g, -g, p.SERVO_CASE_H + g)
    tabs = (x0 - p.SERVO_TAB_L - g, x1 + p.SERVO_TAB_L + g, -w - g, w + g,
            p.SERVO_TAB_Z - g, p.SERVO_TAB_Z + p.SERVO_TAB_T + g)
    cap = (-6.0 - g, x1 + g, -w - g, w + g, p.SERVO_CASE_H - g, p.SERVO_CASE_H + p.SERVO_CAP_H + g)
    return case, tabs, cap


@model
def servo():
    """4 g micro servo. Origin on the shaft axis at the case bottom, +Z along the shaft."""
    case, tabs, cap = servo_boxes()
    body = box(*case) + box(*tabs) + box(*cap)
    z = p.SERVO_CASE_H + p.SERVO_CAP_H
    body += zcyl(0, 0, z, z + p.SERVO_SPLINE_H, p.SERVO_SPLINE_D)
    for x in (case[0] - p.SERVO_TAB_L / 2, case[1] + p.SERVO_TAB_L / 2):
        body -= zcyl(x, 0, p.SERVO_TAB_Z - 1, p.SERVO_TAB_Z + p.SERVO_TAB_T + 1, 1.6)
    body.label = "servo"
    body.material = plastics.abs_()
    body.color = "#2f6fb5"
    return body


@model
def horn():
    """Single-arm servo horn. Origin on the shaft axis at the horn's top face, arm along +X, hub down (-Z)."""
    hub = zcyl(0, 0, -2.75, 0, 7.5)
    arm = bd.Pos(0, 0, -1.5) * bd.extrude(bd.Pos(7.0, 0) * bd.SlotOverall(18.0, 4.6), 1.5)
    body = hub + arm - zcyl(0, 0, -3, 1, p.SERVO_SPLINE_D)
    for x in (6.0, 11.0):
        body -= zcyl(x, 0, -2, 1, 1.0)
    body.label = "horn"
    body.material = plastics.pom()
    body.color = "#f4f4f0"
    return body


@model
def battery():
    """1S 300 mAh LiPo, centred on its own origin."""
    body = bd.Box(*p.BATTERY)
    body.label = "battery"
    body.color = "#8a8f98"
    return body


@model
def mcu():
    """Controller board (ESP32 super-mini class). Origin at the centre of its underside."""
    L, W, T = p.MCU
    body = box(-L / 2, L / 2, -W / 2, W / 2, 0, T)
    body += box(-L / 2, -L / 2 + 7, -4.5, 4.5, T, T + 3.2)      # USB-C socket
    body += box(-2, 8, -5, 5, T, T + 1.0)                       # module can
    body.label = "mcu"
    body.color = "#1f6b3a"
    return body


# ----------------------------------------------------------------------------- printed parts


def hip_servo_cut(sx, sy):
    """What one hip servo needs cut out of the tray, in the world: its envelope grown by FIT, open to the top."""
    cuts = []
    for x0, x1, y0, y1, z0, z1 in servo_boxes(p.FIT):
        # servo x -> world x * sx (about the hip axis), servo z -> world y * sy, servo y -> world z
        wx0, wx1 = sx * (p.HIP_X + x0), sx * (p.HIP_X + x1)
        wy0, wy1 = sy * (p.HIP_Y0 + z0), sy * (p.HIP_Y0 + z1)
        cuts.append(box(wx0, wx1, wy0, wy1, y0, p.TRAY_Z1 + 1))
    return cuts


DECK_SCREWS = [(sx * 17.3, sy * 14.4) for sx in (1, -1) for sy in (1, -1)]


@model
def tray():
    """Chassis tray: four hip-servo pockets and the battery bay, open at the top. Prints as modelled."""
    body = box(-p.TRAY_X, p.TRAY_X, -p.TRAY_Y, p.TRAY_Y, p.TRAY_Z0, p.TRAY_Z1)
    cuts = []
    for sx, sy in p.LEGS.values():
        cuts += hip_servo_cut(sx, sy)
    floor = -p.SERVO_W / 2 - p.FIT
    bx, by = p.BATTERY[0] / 2 + 0.5, p.BATTERY[1] / 2 + 0.5
    cuts.append(box(-bx, bx, -by, by, floor, p.TRAY_Z1 + 1))                 # battery bay
    cuts.append(box(-23.5, 23.5, -1.5, 1.5, 0.5, p.TRAY_Z1 + 1))             # cable channel along the web
    # Lightening: windows through the floor under each servo and the battery, pockets beside the battery.
    cuts.append(box(-bx + 3, bx - 3, -by + 3, by - 3, p.TRAY_Z0 - 1, floor + 1))
    for sx, sy in p.LEGS.values():
        cuts.append(box(sx * 26.0, sx * 40.5, sy * 3.5, sy * 14.0, p.TRAY_Z0 - 1, floor + 1))
    for sy in (1, -1):
        cuts.append(box(-13.5, 13.5, sy * (by + 1.2), sy * (p.TRAY_Y - 1.2), floor, p.TRAY_Z1 + 1))
    for x, y in DECK_SCREWS:
        cuts.append(zcyl(x, y, p.TRAY_Z1 - 6, p.TRAY_Z1 + 1, 1.3))           # pilot holes, M1.6 self-tapping
    body -= cuts
    body.label = "tray"
    body.material = plastics.pla()
    body.color = PRINTED
    return body


@model
def deck():
    """Top plate: closes the tray, clamps the servos and carries the controller. Origin at its underside centre."""
    body = box(-p.TRAY_X, p.TRAY_X, -p.TRAY_Y, p.TRAY_Y, 0, p.DECK_T)
    L, W, _ = p.MCU
    for sx in (1, -1):
        for sy in (1, -1):
            body += zcyl(sx * (L / 2 - 2), sy * (W / 2 - 2), p.DECK_T, p.DECK_T + 2.0, 3.6)   # board standoffs
    cuts = [zcyl(x, y, -1, p.DECK_T + 1, 1.9) for x, y in DECK_SCREWS]
    cuts.append(box(-4, 4, -W / 2 - 5, -W / 2 - 1.5, -1, p.DECK_T + 1))                    # cable slot
    cuts.append(box(-4, 4, W / 2 + 1.5, W / 2 + 5, -1, p.DECK_T + 1))
    body -= cuts
    body.label = "deck"
    body.material = plastics.pla()
    body.color = PRINTED
    return body


@model
def thigh():
    """Thigh bracket: a plate on the hip horn that carries the knee servo.

    Origin on the hip axis at the plate's underside (the hip horn's top face); +X to the knee, +Z outward.
    """
    t = p.THIGH_T
    w = p.SERVO_W / 2
    c0, c1 = p.L1 + p.SERVO_SHAFT_END - p.SERVO_L, p.L1 + p.SERVO_SHAFT_END     # knee servo case along X
    x0, x1 = -6.0, c1 + p.SERVO_TAB_L + 2.5
    body = bd.extrude(bd.Pos((x0 + x1) / 2, 0) * bd.SlotOverall(x1 - x0, 13.0), t)
    tab_z = t + p.SERVO_TAB_Z
    body += box(c0 - p.SERVO_TAB_L, c0 - p.FIT, -w, w, t, tab_z)                 # posts under the servo tabs
    body += box(c1 + p.FIT, c1 + p.SERVO_TAB_L, -w, w, t, tab_z)
    for s in (1, -1):                                                           # rails that locate the case
        body += box(c0, c1, s * (w + p.FIT), s * 6.5, t, t + 4.0)
    cuts = [zcyl(0, 0, -1, t + 1, 2.4)]                                         # horn screw
    cuts += [zcyl(x, 0, -1, t + 1, 1.2) for x in (6.0, 11.0)]                   # horn arm screws
    for x in (c0 - p.SERVO_TAB_L / 2, c1 + p.SERVO_TAB_L / 2):
        cuts.append(zcyl(x, 0, tab_z - 6, tab_z + 1, 1.2))                      # tab screw pilots
    body -= cuts
    body.label = "thigh"
    body.material = plastics.pla()
    body.color = PRINTED
    return body


@model
def shank():
    """Shank: a plate on the knee horn ending in a peg for the foot.

    Origin on the knee axis at the plate's underside (the knee horn's top face); +X to the foot, +Z outward.
    """
    t = p.SHANK_T
    x0, x1 = -5.5, p.L2 - p.FOOT_R - 0.5
    body = bd.extrude(bd.Pos((x0 + x1) / 2, 0) * bd.SlotOverall(x1 - x0, 9.0), t)
    body += box(x1 - 3, p.L2 + 1.5, -t / 2, t / 2, 0, t)                        # square peg into the foot
    cuts = [zcyl(0, 0, -1, t + 1, 2.4)] + [zcyl(x, 0, -1, t + 1, 1.2) for x in (6.0, 11.0)]
    body -= cuts
    body.label = "shank"
    body.material = plastics.pla()
    body.color = PRINTED
    return body


FOOT_FLAT = 3.1   # the foot's flat face below the ball's centre: it stands on it to print


@model
def foot():
    """TPU ball foot, pressed on the shank's peg. As printed: flat face down, the peg's socket up from it.

    The ball's centre is at (0, 0, FOOT_FLAT).
    """
    t = p.SHANK_T
    body = bd.Pos(0, 0, FOOT_FLAT) * bd.Sphere(p.FOOT_R)
    body -= box(-6, 6, -6, 6, -6, 0)                                   # the flat
    body -= box(-t / 2, t / 2, -t / 2, t / 2, -1, FOOT_FLAT + 1.5)     # socket for the 2.5 mm square peg
    body.label = "foot"
    body.material = plastics.tpu()
    body.color = DARK
    return body


if __name__ == "__main__":
    for part in (servo, horn, battery, mcu, tray, deck, thigh, shank, foot):
        part()
