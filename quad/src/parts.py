"""The quadruped's parts, each a model in the frame it is used in.

Printed parts are PLA on an FDM printer and are modelled as they print: flat face down, Z up.

Check: cad model dfm "$ID" --process printing --technology fdm --material pla
"""
import math

import build123d as bd
from bd_materials import plastics
from cad import model

import params as p

SHELL = "#ece8df"     # matte warm white: the shell
FRAME = "#2f3338"     # graphite: chassis and legs
DARK = "#17191c"      # servos and feet
VISOR = "#ff9a2ecc"   # smoked amber, see-through: the sensor strip


def box(x0, x1, y0, y1, z0, z1):
    """An axis-aligned box from its corners."""
    lo = (min(x0, x1), min(y0, y1), min(z0, z1))
    size = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    return bd.Pos(lo[0] + size[0] / 2, lo[1] + size[1] / 2, lo[2] + size[2] / 2) * bd.Box(*size)


def zcyl(x, y, z0, z1, d):
    """A cylinder along Z."""
    return bd.Pos(x, y, (z0 + z1) / 2) * bd.Cylinder(d / 2, abs(z1 - z0))


def stadium(half_length, radius, height):
    """A stadium (two half discs joined by a rectangle) along X, extruded up from z = 0."""
    return bd.extrude(bd.SlotOverall(2 * (half_length + radius), 2 * radius), height)


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
    body.color = DARK
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


CORNER_R = 3.0

# The deck's lip: a stadium ring. The shell's collar presses over it and the controller board rests on it.
LIP_HALF, LIP_R, LIP_WALL = 9.0, 9.5, 1.2
LIP_H = 6.0

DECK_SCREWS = [(sx * 17.3, sy * 14.4) for sx in (1, -1) for sy in (1, -1)]


@model
def tray():
    """Chassis tray: four hip-servo pockets and the battery bay, open at the top. Prints as modelled."""
    body = box(-p.TRAY_X, p.TRAY_X, -p.TRAY_Y, p.TRAY_Y, p.TRAY_Z0, p.TRAY_Z1)
    body = bd.fillet(body.edges().filter_by(bd.Axis.Z), CORNER_R)             # rounded plan
    body = bd.chamfer(body.edges().group_by(bd.Axis.Z)[0], 0.8)               # a soft belly, 45 deg: prints
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
    body.color = FRAME
    return body


@model
def deck():
    """Top plate: closes the tray, clamps the servos; its lip locates the shell and carries the controller.

    Origin at its underside centre.
    """
    body = box(-p.TRAY_X, p.TRAY_X, -p.TRAY_Y, p.TRAY_Y, 0, p.DECK_T)
    body = bd.fillet(body.edges().filter_by(bd.Axis.Z), CORNER_R)
    lip = stadium(LIP_HALF, LIP_R, LIP_H) - stadium(LIP_HALF, LIP_R - LIP_WALL, LIP_H)
    body += bd.Pos(0, 0, p.DECK_T) * lip
    cuts = [zcyl(x, y, -1, p.DECK_T + 1, 1.9) for x, y in DECK_SCREWS]
    for sx in (1, -1):
        cuts.append(box(sx * 9.5, sx * 13.5, -3, 3, -1, p.DECK_T + 1))        # cables come up under the board
    body -= cuts
    body.label = "deck"
    body.material = plastics.pla()
    body.color = FRAME
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
    # Outline: a round hip, a waist, then the knee servo's bed.
    upper = bd.Spline([(2.5, 6.0), (7.0, 4.7), (11.0, 5.3), (15.5, 6.5)], tangents=[(1, -0.6), (1, 0.45)])
    lower = bd.Spline([(15.5, -6.5), (11.0, -5.3), (7.0, -4.7), (2.5, -6.0)], tangents=[(-1, 0.45), (-1, -0.6)])
    neck = bd.make_face([upper, bd.Line((15.5, 6.5), (15.5, -6.5)), lower, bd.Line((2.5, -6.0), (2.5, 6.0))])
    outline = bd.Circle(6.5) + neck + bd.Pos((9.0 + x1) / 2, 0) * bd.SlotOverall(x1 - 9.0, 13.0)
    body = bd.extrude(outline, t)
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
    body.color = FRAME
    return body


FOOT_FLAT = 3.1   # the foot's flat face below the ball's centre: it stands on it to print


def leg_line(hand, x):
    """The lower leg's centreline (y at x): straight over the horn, one smooth bow, straight into the foot."""
    xs, xe = 9.0, p.L2 - FOOT_FLAT - 0.4
    if x <= xs:
        return 0.0
    u = ((x - xs) / (xe - xs)) ** 1.4          # the bow leans towards the foot
    return hand * 4.2 * math.sin(math.pi * u) ** 2


def lower_leg(hand):
    """Lower leg: a tapered, bowed plate on the knee horn ending in a peg for the foot.

    Origin on the knee axis at the plate's underside (the knee horn's top face); +X to the foot, +Z outward.
    hand = +1 or -1 picks the side the bow bulges to, so left and right legs mirror each other.
    """
    t = p.SHANK_T
    xe = p.L2 - FOOT_FLAT - 0.4                      # the plate stops just short of the foot's flat
    xs = [3.5 + (xe - 3.5) * i / 11 for i in range(12)]
    half = lambda x: 4.3 - 2.6 * (x - 3.5) / (xe - 3.5)     # 8.6 mm wide at the knee, 3.4 mm at the foot
    up = [(x, leg_line(hand, x) + half(x)) for x in xs]
    down = [(x, leg_line(hand, x) - half(x)) for x in reversed(xs)]
    face = bd.make_face([bd.Spline(up, tangents=[(1, 0), (1, 0)]), bd.Line(up[-1], down[0]),
                         bd.Spline(down, tangents=[(-1, 0), (-1, 0)]), bd.Line(down[-1], up[0])])
    body = bd.extrude(bd.Circle(5.6) + face, t)
    body += box(xe - 1.0, p.L2 + 1.5, -t / 2, t / 2, 0, t)                        # square peg into the foot
    cuts = [zcyl(0, 0, -1, t + 1, 2.4)] + [zcyl(x, 0, -1, t + 1, 1.2) for x in (6.0, 11.0)]
    body -= cuts
    body.label = "shank"
    body.material = plastics.pla()
    body.color = FRAME
    return body


@model
def shank_a():
    return lower_leg(1)


@model
def shank_b():
    return lower_leg(-1)


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


# ----------------------------------------------------------------------------- shell and visor

# The shell: a river-pebble dome with a stadium plan, over the whole chassis. Its cross-section is two
# tangent arcs: a tight shoulder from the rim, then a wide crown. Numbers are in the shell's own frame,
# its rim on z = 0. In the robot the rim stands SHELL_GAP above the deck, clear of the legs.
SHELL_HALF = 13.5     # half length of the straight middle
SHELL_RIM = 36.0      # radius at the rim: half the shell's width
SHELL_R1 = 14.0       # shoulder radius
SHELL_TURN = 60.0     # degrees the shoulder turns before the crown takes over
SHELL_WALL = 1.0
SHELL_GAP = 2.0       # rim above the deck's top
SHELL_R2 = (SHELL_RIM - SHELL_R1 * (1 - math.cos(math.radians(SHELL_TURN)))) / math.cos(math.radians(SHELL_TURN))
SHELL_H = SHELL_R2 - (SHELL_R2 - SHELL_R1) * math.sin(math.radians(SHELL_TURN))   # rim to the top of the crown

VISOR_Z = (5.6, 8.8)  # the visor's slit, above the rim: a band on the shoulder
VISOR_AZ = 42.0       # and this far to each side of straight ahead, around the front end's axis
VISOR_T = 1.8         # the visor strip's thickness: flush outside, 0.8 mm proud inside


def pebble(inset):
    """The dome as a solid, `inset` mm inside the outer surface (0 = the outer surface itself)."""
    r1, r2, rim = SHELL_R1 - inset, SHELL_R2 - inset, SHELL_RIM - inset
    a = math.radians(SHELL_TURN)
    c1 = (SHELL_RIM - SHELL_R1, 0.0)                                  # shoulder centre (r, z)
    c2 = (0.0, (SHELL_R1 - SHELL_R2) * math.sin(a))                   # crown centre, on the axis
    top = (0.0, c2[1] + r2)
    half = [bd.Line((0, -3), (rim, -3)), bd.Line((rim, -3), (rim, 0)),
            bd.Pos(*c1) * bd.CenterArc((0, 0), r1, 0, SHELL_TURN),
            bd.Pos(*c2) * bd.CenterArc((0, 0), r2, SHELL_TURN, 90 - SHELL_TURN),
            bd.Line(top, (0, -3))]
    face = bd.make_face(half)                                         # the half section: x = radius, y = height
    ends = [bd.Pos(sx * SHELL_HALF, 0, 0) * bd.revolve(bd.Plane.XZ * face, bd.Axis.Z) for sx in (1, -1)]
    full = face + bd.mirror(face, about=bd.Plane.YZ)                   # the full section, across the robot
    middle = bd.extrude(bd.Plane.YZ * full, SHELL_HALF, both=True)
    return middle + ends


def visor_zone(z0, z1, half_angle):
    """A wedge of space around the front end's axis: between two heights, `half_angle` to each side of ahead."""
    n = 12
    arc = [(SHELL_HALF + 60 * math.cos(math.radians(a)), 60 * math.sin(math.radians(a)))
           for a in (-half_angle + 2 * half_angle * i / n for i in range(n + 1))]
    return bd.Pos(0, 0, z0) * bd.extrude(bd.Polygon((SHELL_HALF, 0), *arc, align=None), z1 - z0)


@model
def shell():
    """The shell: a hollow pebble with a slit for the visor across its front and a collar inside.

    Origin at the centre of its rim. Prints rim down; the ceiling needs support inside, where it is not seen.
    """
    body = pebble(0) - pebble(SHELL_WALL)
    body -= box(-80, 80, -80, 80, -6, 0)
    # The collar that presses over the deck's lip: from the rim's plane up to the ceiling.
    grip = LIP_R + 0.2
    collar = stadium(LIP_HALF, grip + 1.2, SHELL_H) - stadium(LIP_HALF, grip, SHELL_H)
    body += collar & pebble(SHELL_WALL / 2)
    body -= visor_zone(*VISOR_Z, VISOR_AZ)
    body.label = "shell"
    body.material = plastics.pla()
    body.color = SHELL
    return body


@model
def visor():
    """The visor: a see-through strip that fills the shell's slit, glued in. In the shell's frame.

    Prints as modelled, standing on its lower edge. A status LED or a distance sensor sits behind it.
    """
    body = (pebble(0) - pebble(VISOR_T)) & visor_zone(VISOR_Z[0] + 0.1, VISOR_Z[1] - 0.1, VISOR_AZ - 0.3)
    body.label = "visor"
    body.material = plastics.petg()
    body.color = VISOR
    return body


if __name__ == "__main__":
    for part in (servo, horn, battery, mcu, tray, deck, thigh, shank_a, shank_b, foot, shell, visor):
        part()
