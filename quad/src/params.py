"""Shared dimensions for the mini quadruped (mm, degrees, grams). Pure Python: no CAD kernel here.

Frames: +X forward, +Y left, +Z up. The hip axes are at z = 0.

SERVO: a 4 g-class micro servo. Envelope from seller listings of the EMAX ES9051
(19.74 x 8.34 x 23.25 mm, 4.1-4.3 g); the GH-S37D (20.05 x 8.75 x 22 mm, 3.7 g) fits the same
pockets. The tab height, cap and shaft offset below are ASSUMED proportions, not from a datasheet:
measure the real servo with calipers before printing.
"""
import math

# --- servo envelope (own frame: origin on the shaft axis at the case bottom, +z along the shaft) ---
SERVO_L = 19.74          # case length (x)
SERVO_W = 8.34           # case width (y)
SERVO_CASE_H = 15.5      # case bottom to case top (assumed)
SERVO_CAP_H = 4.0        # gear cap above the case (assumed)
SERVO_SPLINE_H = 3.75    # output spline above the cap -> total 23.25
SERVO_H = SERVO_CASE_H + SERVO_CAP_H + SERVO_SPLINE_H
SERVO_SHAFT_END = 5.0    # shaft axis to the near end of the case (assumed)
SERVO_TAB_Z = 11.0       # underside of the mounting tabs above the case bottom (assumed)
SERVO_TAB_T = 1.2        # tab thickness (assumed)
SERVO_TAB_L = 3.9        # tab length beyond the case, each end (assumed)
SERVO_SPLINE_D = 4.6
SERVO_MASS = 4.1         # g, with cable
HORN_MASS = 0.2          # g
FIT = 0.3                # clearance around a servo in a printed pocket (FDM)

# --- servo performance used by the simulation (conservative: GH-S37D at 3.6 V, 1S LiPo) ---
SERVO_STALL_NM = 0.5 * 0.0980665          # 0.5 kg*cm -> N*m
SERVO_NOLOAD_RAD_S = math.radians(60) / 0.12   # 0.12 s / 60 deg
SERVO_TRAVEL = 45.0      # +/- deg about centre (a 90 deg servo)

# --- layout ---
HIP_X = 38.0             # hip axis fore/aft of the centre
WEB = 2.0                # central web between the left and right hip servos
HIP_Y0 = WEB / 2         # case bottom of a hip servo
L1 = 30.0                # thigh: hip axis to knee axis
L2 = 30.0                # shank: knee axis to foot centre
STANCE = 35.0            # as built: thigh tilted this far from vertical, shank the same the other way
FOOT_R = 4.5
THIGH_T = 2.0            # thigh plate thickness
SHANK_T = 2.5

HIP_FACE_Y = HIP_Y0 + SERVO_H                 # horn top of a hip servo: the thigh plate sits here
KNEE_FACE_Y = HIP_FACE_Y + THIGH_T + SERVO_H   # horn top of a knee servo: the shank plate sits here
FOOT_Y = KNEE_FACE_Y + SHANK_T / 2

TRAY_X = 49.0            # half length of the chassis
TRAY_Y = HIP_Y0 + SERVO_CASE_H   # half width: flush with the hip servo case tops
TRAY_Z0 = -6.0           # underside
TRAY_Z1 = SERVO_W / 2 + 0.2      # top of the tray = underside of the deck
DECK_T = 1.6

BATTERY = (30.0, 20.0, 6.0)   # 1S 300 mAh LiPo "602030"
BATTERY_MASS = 8.0
MCU = (22.5, 18.0, 1.2)       # ESP32-C3/S3 "super mini" class board
MCU_MASS = 3.0
WIRING_MASS = 3.0             # cables, switch, screws: a lump at the centre

LEGS = {"fl": (1, 1), "fr": (1, -1), "rl": (-1, 1), "rr": (-1, -1)}   # name: (sx, sy)


def leg_frames(sx, sy):
    """World frames of one leg as built. Front knees point back, rear knees forward (> <)."""
    s, c = math.sin(math.radians(STANCE)), math.cos(math.radians(STANCE))
    hip = (sx * HIP_X, 0.0, 0.0)
    u = (-sx * s, 0.0, -c)            # along the thigh, hip to knee
    w = (sx * s, 0.0, -c)             # along the shank, knee to foot
    knee = (hip[0] + L1 * u[0], 0.0, L1 * u[2])
    foot = (knee[0] + L2 * w[0], 0.0, knee[2] + L2 * w[2])
    a = (0.0, float(sy), 0.0)         # outward, along the servo shafts
    return {"hip": hip, "knee": knee, "foot": foot, "u": u, "w": w, "a": a}
