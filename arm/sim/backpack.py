"""Escena del morral: el brazo SO-101 montado sobre el hombro derecho de una persona que camina.

- El usuario es un cuerpo "mocap" (lo movemos con un patrón de marcha realista: sube y baja
  ~2 cm a 1.8 pasos/s, se balancea de lado, gira un poco la cadera).
- El morral + soporte es un cuerpo libre "soldado" (weld) al usuario: así el brazo recibe las
  aceleraciones reales del caminar (no se teletransporta).
- La IMU va en la base del brazo (como un BNO055 en el soporte).
- En la vereda hay personas paradas (con cara color piel, que el detector busca).

Ejes del usuario: x = adelante, y = izquierda, z = arriba; origen = centro de los hombros.
"""

import os
from dataclasses import dataclass

import mujoco
import numpy as np

import scene
from scene import B, CAP, P, S, _geom, add_person

SHOULDER_H = 1.45  # m, altura de los hombros (persona de ~1.75 m)
# Base del brazo respecto del centro de los hombros: atrás, en el borde del hombro derecho, a la
# altura de los hombros (más adentro queda a menos de 10 cm de la cabeza)
MOUNT = np.array([-0.10, -0.26, 0.0])
HEAD = np.array([0.02, 0.0, 0.2])  # centro de la cabeza del usuario
HEAD_R = 0.10
STEP_HZ = 1.8  # pasos por segundo
WALK_SPEED = 1.2  # m/s
# Personas en la vereda: (nombre, x, y). Las de la izquierda quedan del otro lado de la cabeza.
BYSTANDERS = [("ana", 6.0, -1.7), ("beto", 10.0, 1.8), ("caro", 16.0, -0.9)]


def mount_xml():
    """so101.xml con la base del brazo dentro de un cuerpo libre "mount" (el morral)."""
    src = scene.ensure_model()
    out = src.with_name("so101_mount.xml")
    xml = src.read_text()
    a = xml.index("<!-- Link base -->")
    b = xml.rindex("</worldbody>")
    wrapped = (xml[:a] + '<body name="mount">\n<freejoint name="mount"/>\n' + xml[a:b] + "</body>\n" + xml[b:])
    if not out.exists() or out.read_text() != wrapped:
        # Escritura atómica: varios procesos pueden armar la escena a la vez
        tmp = out.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(wrapped)
        os.replace(tmp, out)
    return out


def build(volts="12V") -> mujoco.MjModel:
    return build_spec(volts).compile()


def build_spec(volts="12V") -> mujoco.MjSpec:
    """La escena sin compilar (para agregarle objetos)."""
    spec = mujoco.MjSpec.from_file(str(mount_xml()))
    scene.configure_arm(spec, volts)
    w = spec.worldbody
    sky = spec.add_texture()
    sky.name, sky.type, sky.builtin = "sky", mujoco.mjtTexture.mjTEXTURE_SKYBOX, mujoco.mjtBuiltin.mjBUILTIN_GRADIENT
    sky.rgb1, sky.rgb2, sky.width, sky.height = [0.55, 0.7, 0.9], [0.2, 0.3, 0.5], 256, 1536
    light = w.add_light()
    light.pos, light.dir, light.type = [5, -2, 6], [0.3, 0.3, -1], mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    light.castshadow = True

    # Vereda, calle y edificios (colores fríos: no se confunden con piel)
    _geom(w, "floor", P, (0, 0, 0.05), (0, 0, 0), (0.33, 0.35, 0.38, 1))
    _geom(w, "sidewalk", B, (14, 1.5, 0.005), (8, 0, 0.005), (0.6, 0.62, 0.66, 1))
    for i, x in enumerate(np.arange(-2, 22, 4.0)):
        _geom(w, None, B, (1.8, 0.8, 1.6 + 0.6 * (i % 3)), (x, 3.6, 1.6 + 0.6 * (i % 3)), (0.45, 0.55, 0.68, 1))
    for x, y in [(4, -2.6), (13, -2.6)]:
        _geom(w, None, CAP, (0.06, 1.5), (x, y, 1.5), (0.3, 0.3, 0.32, 1))  # postes

    for name, x, y in BYSTANDERS:
        add_person(w, name, [x, y, 0.0], face_z=1.62)  # miran hacia -x: hacia el usuario que llega

    # Usuario (mocap): cabeza con capucha (no color piel, para no "verse" a sí mismo), torso,
    # brazos y piernas. Piernas y brazos son mocap aparte para animar la marcha.
    u = w.add_body()
    u.name, u.mocap, u.pos = "wearer", True, [0, 0, SHOULDER_H]
    nc = dict(contype=0, conaffinity=0)
    _geom(u, "wearer_head", S, (HEAD_R,), HEAD, (0.35, 0.37, 0.42, 1), **nc)
    _geom(u, None, CAP, (0.05, 0.04), (0.01, 0, 0.07), (0.35, 0.37, 0.42, 1), **nc)
    _geom(u, None, B, (0.11, 0.19, 0.28), (0, 0, -0.27), (0.2, 0.45, 0.35, 1), **nc)
    for side in ("left", "right"):
        for limb, top, length, r in [("leg", -0.55, 0.85, 0.07), ("arm", -0.02, 0.55, 0.045)]:
            y = (0.09 if limb == "leg" else 0.23) * (1 if side == "left" else -1)
            lb = w.add_body()
            lb.name, lb.mocap, lb.pos = f"{side}_{limb}", True, [0, y, SHOULDER_H + top]
            _geom(lb, None, CAP, (r, length / 2), (0, 0, -length / 2), (0.2, 0.2, 0.28, 1) if limb == "leg"
                  else (0.2, 0.45, 0.35, 1), **nc)

    # Morral + soporte: cuerpo libre soldado al usuario. Su origen es la base del brazo.
    mb = spec.body("mount")
    mb.pos = list(MOUNT + [0, 0, SHOULDER_H])
    to_user = -MOUNT  # del soporte al centro de los hombros
    _geom(mb, "backpack", B, (0.08, 0.16, 0.22), to_user + [-0.2, 0, -0.18], (0.75, 0.35, 0.15, 1),
          mass=2.5, **nc)
    _geom(mb, "bracket", CAP, (0.012, 0), rgba=(0.15, 0.15, 0.15, 1), mass=0.15, fromto=list(
        np.r_[to_user + [-0.12, -0.12, -0.05], [0.0, 0.0, -0.005]]), **nc)
    _geom(mb, "plate", B, (0.05, 0.04, 0.004), (0.0, 0, -0.004), (0.15, 0.15, 0.15, 1), mass=0.05, **nc)
    s = mb.add_site()
    s.name, s.pos = "mount_imu", [0, 0, -0.01]
    gyro = spec.add_sensor()
    gyro.name, gyro.type, gyro.objtype, gyro.objname = ("mount_gyro", mujoco.mjtSensor.mjSENS_GYRO,
                                                       mujoco.mjtObj.mjOBJ_SITE, "mount_imu")
    eq = spec.add_equality()
    eq.type, eq.objtype, eq.name1, eq.name2 = (mujoco.mjtEq.mjEQ_WELD, mujoco.mjtObj.mjOBJ_BODY,
                                               "mount", "wearer")
    eq.solref = [0.01, 1]

    # Cámara que acompaña al usuario (de costado y adelante), sin el vaivén
    cb = w.add_body()
    cb.name, cb.mocap, cb.pos = "follow_cam", True, [0, 0, 0]
    cam = cb.add_camera()
    cam.name, cam.pos = "follow", [-0.95, -0.85, 2.0]  # por encima del hombro, desde atrás
    cam.mode, cam.targetbody = mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY, "cam_target"
    tb = w.add_body()  # punto al que mira: un poco adelante del usuario, sin el vaivén
    tb.name, tb.mocap, tb.pos = "cam_target", True, [0.6, -0.25, 1.5]
    return spec


def _yaw_quat(yaw):
    return [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]


def _euler_quat(roll, pitch, yaw):
    q = np.zeros(4)
    mujoco.mju_euler2Quat(q, np.array([roll, pitch, yaw]), "xyz")
    return q


@dataclass
class Walk:
    """Recorrido: parado, camina, se detiene. speed(t) en m/s con arranques suaves."""

    start: float = 2.0
    stop: float = 15.5
    speed_max: float = WALK_SPEED

    def speed(self, t):
        ramp = 0.8
        if t < self.start or t > self.stop + ramp:
            return 0.0
        if t < self.start + ramp:
            return self.speed_max * (t - self.start) / ramp
        if t > self.stop:
            return self.speed_max * (1 - (t - self.stop) / ramp)
        return self.speed_max


class Wearer:
    """Mueve al usuario (y sus brazos y piernas) con un patrón de marcha."""

    def __init__(self, model, data, walk=None):
        self.m, self.d = model, data
        self.walk = walk or Walk()
        self.x, self.phase = 0.0, 0.0
        ids = {n: model.body(n).mocapid[0] for n in
               ("wearer", "left_leg", "right_leg", "left_arm", "right_arm", "follow_cam", "cam_target")}
        self.ids = ids
        self.limb0 = {n: data.mocap_pos[i].copy() for n, i in ids.items()}

    def update(self, t, dt):
        v = self.walk.speed(t)
        k = v / WALK_SPEED  # intensidad de la marcha
        self.x += v * dt
        self.phase += 2 * np.pi * STEP_HZ * dt * (k > 0.01)
        ph = self.phase
        d, ids = self.d, self.ids
        # Centro de los hombros: sube y baja dos veces por ciclo (una por paso), se balancea una vez
        pos = np.array([self.x, 0.02 * k * np.sin(ph / 2), SHOULDER_H + 0.02 * k * np.cos(ph)])
        d.mocap_pos[ids["wearer"]] = pos
        d.mocap_quat[ids["wearer"]] = _euler_quat(0.035 * k * np.sin(ph / 2), 0.04 * k + 0.02 * k * np.sin(ph),
                                                  0.05 * k * np.sin(ph / 2))
        for side, sgn in (("left", 1), ("right", -1)):
            for limb, amp in (("leg", 0.35), ("arm", -0.3)):
                n = f"{side}_{limb}"
                p0 = self.limb0[n]
                d.mocap_pos[ids[n]] = [self.x + p0[0], p0[1], p0[2] + (pos[2] - SHOULDER_H)]
                d.mocap_quat[ids[n]] = _euler_quat(0, sgn * amp * k * np.sin(ph / 2), 0)
        d.mocap_pos[ids["follow_cam"]] = [self.x, 0, 0]
        d.mocap_pos[ids["cam_target"]] = [self.x + 0.6, -0.25, 1.5]

    def head_center(self):
        i = self.ids["wearer"]
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, self.d.mocap_quat[i])
        return self.d.mocap_pos[i] + R.reshape(3, 3) @ HEAD
