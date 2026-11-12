"""The quadruped as a MuJoCo model: collision shapes, servo dynamics and position actuators.

Run:  cad run src/quad_mujoco.py   ->  sim/quad.xml (+ sim/assets/, and sim/scene.xml once)
"""
import mujoco
from cad.mujoco import collisions, fit, parts, save, spec

import params as p
from robot import quad

# A hobby servo's loop: full torque at about 4 deg of error (digital micro servo; tuned, not measured).
KP = p.SERVO_STALL_NM / 0.07
# DC-motor torque-speed line as viscous damping: stall torque at 0, nothing at the no-load speed.
DAMPING = p.SERVO_STALL_NM / p.SERVO_NOLOAD_RAD_S
# Reflected rotor inertia: a 6 mm coreless rotor (~1e-9 kg*m^2) through ~1:250 gears. Tuned order of magnitude.
ARMATURE = 6e-5
FRICTIONLOSS = 0.002   # N*m, gear train dry friction (tuned)
FOOT_FRICTION = [0.8, 0.005, 0.0001]   # TPU on a table top


def quad_mujoco(kp=KP, stall=p.SERVO_STALL_NM, foot_friction=FOOT_FRICTION) -> mujoco.MjSpec:
    s = spec(quad())

    # Collisions: ball feet, boxes for what touches the floor in a fall, nothing for the rest.
    for path in parts(s):
        leaf = path.split("/")[-1]
        if leaf == "foot":
            leg = path.split("/")[-2].split("_")[-1]
            for geom in fit(s, path, "sphere"):
                # fit() gives the sphere around the part's box: use the ball's own radius and centre (its frame).
                geom.size = [p.FOOT_R / 1000, 0, 0]
                geom.pos = s.site(f"foot_{leg}").pos
                geom.friction = foot_friction
                geom.condim = 4
        elif leaf in ("tray", "shell", "knee_servo"):
            fit(s, path, "box")
        # The lower leg collides as nothing: a box around its bowed plate would reach below the ball foot,
        # and the robot would stand on the box's corner instead of the foot.
        else:
            for geom in collisions(s, path):
                s.delete(geom)

    for name in p.LEGS:
        for kind in ("hip", "knee"):
            joint = s.joint(f"{kind}_{name}")
            joint.armature = ARMATURE
            joint.damping = [DAMPING, 0, 0]
            joint.frictionloss = FRICTIONLOSS
            joint.actfrcrange = [-stall, stall]
            act = s.add_actuator(name=f"{kind}_{name}", target=f"{kind}_{name}",
                                 trntype=mujoco.mjtTrn.mjTRN_JOINT)
            act.set_to_position(kp=kp, inheritrange=True)

    # Sensors for the tests: body attitude and rates.
    s.add_sensor(name="chassis_quat", type=mujoco.mjtSensor.mjSENS_FRAMEQUAT,
                 objtype=mujoco.mjtObj.mjOBJ_BODY, objname="chassis")
    s.add_sensor(name="chassis_gyro", type=mujoco.mjtSensor.mjSENS_FRAMEANGVEL,
                 objtype=mujoco.mjtObj.mjOBJ_BODY, objname="chassis")
    return s


if __name__ == "__main__":
    save(quad_mujoco(), "sim/quad.xml")
