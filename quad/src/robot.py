"""Mini quadruped: 8 x 4 g servos (hip and knee pitch per leg), 1S LiPo, printed PLA, under a pebble shell.

As built = every servo at its centre = the standing pose; every joint turns about world +Y.
"""
import build123d as bd
from cad import model
from cad.build123d import configuration_sequence, frame, free, limits, mass, mechanism_state, point_mass

import params as p
from gait import crawl, dance, stand, trot, wave
from parts import (FOOT_FLAT, LIP_H, SHELL_GAP, battery, deck, foot, horn, mcu, servo, shank_a, shank_b, shell,
                   thigh, tray, visor)


def placed(part, plane, label, local=None):
    shape = plane.location * (local * part if local is not None else part)
    shape.label = label
    return shape


@model
def quad():
    servo_, horn_ = servo().shape, horn().shape

    # ---- chassis: tray, deck, the four hip servos, battery, controller
    tray_ = tray().shape
    point_mass(tray_, p.WIRING_MASS, bd.Pos(0, 0, 0), name="wiring")
    deck_ = bd.Pos(0, 0, p.TRAY_Z1) * deck().shape
    deck_.label = "deck"
    floor = -p.SERVO_W / 2 - p.FIT
    battery_ = bd.Pos(0, 0, floor + p.BATTERY[2] / 2) * battery().shape
    battery_.label = "battery"
    mass(battery_, p.BATTERY_MASS)
    mcu_ = bd.Pos(0, 0, p.TRAY_Z1 + p.DECK_T + LIP_H) * mcu().shape     # resting on the deck's lip
    mcu_.label = "mcu"
    mass(mcu_, p.MCU_MASS)
    # The shell over everything, its rim just above the deck, and the visor in its slit.
    shell_z = p.TRAY_Z1 + p.DECK_T + SHELL_GAP
    shell_ = bd.Pos(0, 0, shell_z) * shell().shape
    shell_.label = "shell"
    visor_ = bd.Pos(0, 0, shell_z) * visor().shape
    visor_.label = "visor"
    chassis_parts = [tray_, deck_, battery_, mcu_, shell_, visor_]
    for name, (sx, sy) in p.LEGS.items():
        plane = bd.Plane(origin=(sx * p.HIP_X, sy * p.HIP_Y0, 0), x_dir=(sx, 0, 0), z_dir=(0, sy, 0))
        s = placed(servo_, plane, f"hip_servo_{name}")
        mass(s, p.SERVO_MASS)
        chassis_parts.append(s)
    chassis = bd.Compound(children=chassis_parts, label="chassis")

    # ---- legs
    links = [chassis]
    for name, (sx, sy) in p.LEGS.items():
        f = p.leg_frames(sx, sy)
        hip_o = (f["hip"][0], sy * p.HIP_FACE_Y, f["hip"][2])
        knee_o = (f["knee"][0], sy * p.KNEE_FACE_Y, f["knee"][2])
        thigh_plane = bd.Plane(origin=hip_o, x_dir=f["u"], z_dir=f["a"])
        shank_plane = bd.Plane(origin=knee_o, x_dir=f["w"], z_dir=f["a"])

        hip_horn = placed(horn_, thigh_plane, "hip_horn")
        mass(hip_horn, p.HORN_MASS)
        bracket = placed(thigh().shape, thigh_plane, "thigh")
        knee_servo = placed(servo_, thigh_plane, "knee_servo", bd.Pos(p.L1, 0, p.THIGH_T))
        mass(knee_servo, p.SERVO_MASS)
        thigh_link = bd.Compound(children=[hip_horn, bracket, knee_servo], label=f"thigh_{name}")

        knee_horn = placed(horn_, shank_plane, "knee_horn")
        mass(knee_horn, p.HORN_MASS)
        plate = placed((shank_a if sx * sy > 0 else shank_b)().shape, shank_plane, "shank")   # curls mirror left/right
        # The foot is modelled as printed (flat down, socket up): turn its +Z onto the shank's +X.
        ball = placed(foot().shape, shank_plane, "foot",
                      bd.Pos(p.L2 - FOOT_FLAT, 0, p.PEG / 2) * bd.Rot(0, 90, 0))
        frame(ball, f"foot_{name}", bd.Pos(0, 0, FOOT_FLAT))            # the ball's centre, in the foot's own frame
        shank_link = bd.Compound(children=[knee_horn, plate, ball], label=f"shank_{name}")

        travel = (-p.SERVO_TRAVEL, p.SERVO_TRAVEL)
        hip = bd.RevoluteJoint(f"hip_{name}", chassis, axis=bd.Axis(hip_o, (0, 1, 0)), angular_range=travel)
        bd.RigidJoint(f"hip_{name}", thigh_link, hip.location)
        hip.connect_to(thigh_link.joints[f"hip_{name}"], angle=0)
        knee = bd.RevoluteJoint(f"knee_{name}", thigh_link, axis=bd.Axis(knee_o, (0, 1, 0)), angular_range=travel)
        bd.RigidJoint(f"knee_{name}", shank_link, knee.location)
        knee.connect_to(shank_link.joints[f"knee_{name}"], angle=0)
        links += [thigh_link, shank_link]

    robot = bd.Compound(children=links, label="quad")
    for name in p.LEGS:
        for joint in (f"hip_{name}", f"knee_{name}"):
            limits(robot, joint, effort=p.SERVO_STALL_NM, velocity=p.SERVO_NOLOAD_RAD_S)
    free(robot)

    mechanism_state(robot, "home")
    mechanism_state(robot, "stand", **stand(height=46.0))
    mechanism_state(robot, "crouch", **stand(height=36.0))
    # The moves the simulation uses, here with the chassis as the fixed link: one steady stride of each gait,
    # and the two tricks whole.
    configuration_sequence(robot, "trot", lambda t: trot(t + 1.0, freq=2.0), duration=0.5)
    configuration_sequence(robot, "crawl", lambda t: crawl(t + 1.0, freq=1.0), duration=1.0)
    configuration_sequence(robot, "wave", wave, duration=5.0)
    configuration_sequence(robot, "dance", dance, duration=6.0)
    return robot


if __name__ == "__main__":
    quad()
