"""Escena de la mesa: brazo SO-101 + mesa + objetos + una "persona" que se mueve.

El modelo del brazo es el oficial de MuJoCo Menagerie (robotstudio_so101, Apache 2.0). No se
copia al repo: se descarga una vez en arm/third_party/ con una versión fija (MENAGERIE_COMMIT).

Ejes: x = adelante del brazo, y = izquierda, z = arriba. La base del brazo está en (0, 0, 0)
sobre la mesa.
"""

import subprocess
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
THIRD = ROOT / "third_party"
SO101_DIR = THIRD / "so101"
MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"
MENAGERIE_COMMIT = "cda5236f98383f6fbaa4820c6b18dba892cd087f"

ARM_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
GRIPPER = "gripper"
TABLE_Z = 0.0  # altura de la cubierta de la mesa (la base del brazo está encima)
FLOOR_Z = -0.75

# Feetech STS3215: torque de bloqueo según la versión
STALL_TORQUE = {"7.4V": 1.91, "12V": 2.94}  # N·m (19.5 y 30 kg·cm)
GRIP_TORQUE = 0.8  # N·m: límite de la pinza (en LeRobot se limita igual en el servo)

# Color de piel de la "persona" (el detector de la cámara lo busca)
SKIN = (0.92, 0.72, 0.58, 1)


def ensure_model() -> Path:
    """Descarga el modelo del SO-101 (solo la carpeta necesaria) si no está."""
    xml = SO101_DIR / "so101.xml"
    if xml.exists():
        return xml
    repo = THIRD / "menagerie"
    repo.mkdir(parents=True, exist_ok=True)

    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

    git("init", "-q")
    git("remote", "add", "origin", MENAGERIE_URL)
    git("sparse-checkout", "set", "robotstudio_so101")
    git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", MENAGERIE_COMMIT)
    git("checkout", "-q", "FETCH_HEAD")
    (repo / "robotstudio_so101").rename(SO101_DIR)
    return xml


def _geom(body, name, gtype, size, pos=(0, 0, 0), rgba=(0.8, 0.8, 0.8, 1), **kw):
    g = body.add_geom()
    if name:
        g.name = name
    g.type = gtype
    g.size = list(size) + [0] * (3 - len(size))
    g.pos = list(pos)
    g.rgba = list(rgba)
    for k, v in kw.items():
        setattr(g, k, v)
    return g


def configure_arm(spec, volts):
    """Ajustes del brazo comunes a todas las escenas."""
    spec.option.timestep = 0.005
    # Torque máximo de los servos según la versión elegida
    for a in spec.actuators:
        a.forcerange = [-STALL_TORQUE[volts], STALL_TORQUE[volts]]
    # Pinza: torque limitado (~10 N de apriete). Con todo el torque aplasta y suelta objetos.
    spec.actuator(GRIPPER).forcerange = [-GRIP_TORQUE, GRIP_TORQUE]
    # Las mallas convexas de las mandíbulas tapan el hueco donde va el objeto: se usan solo las
    # cajas y esferas de choque que trae el modelo.
    for g in spec.geoms:
        if g.classname.name == "collision_gripper_mesh":
            g.contype = g.conaffinity = 0
    spec.visual.headlight.ambient = [0.35, 0.35, 0.35]
    spec.visual.headlight.diffuse = [0.6, 0.6, 0.6]
    spec.visual.global_.offwidth, spec.visual.global_.offheight = 1280, 720


B, S, C, P, CAP = (mujoco.mjtGeom.mjGEOM_BOX, mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_CYLINDER,
                   mujoco.mjtGeom.mjGEOM_PLANE, mujoco.mjtGeom.mjGEOM_CAPSULE)


def add_person(parent, name, pos, face_z=0.42, mocap=False):
    """Persona simple: torso, cara color piel (lo que busca el detector), pelo, ojos y boca.

    Mira hacia -x. face_z = altura de la cara sobre `pos`.
    """
    b = parent.add_body()
    b.name, b.pos, b.mocap = name, list(pos), mocap
    nc = dict(contype=0, conaffinity=0)
    _geom(b, None, B, (0.09, 0.17, 0.2), (0.05, 0, face_z - 0.3), (0.25, 0.4, 0.55, 1), **nc)
    if face_z > 1.0:  # de pie: piernas
        for y in (-0.08, 0.08):
            _geom(b, None, CAP, (0.06, (face_z - 0.55) / 2), (0.05, y, (face_z - 0.55) / 2), (0.2, 0.2, 0.25, 1), **nc)
    _geom(b, f"{name}_face" if name != "person" else "face", S, (0.085,), (0, 0, face_z), SKIN, **nc)
    _geom(b, None, S, (0.088,), (0.025, 0, face_z + 0.025), (0.2, 0.13, 0.08, 1), **nc)
    for y in (-0.03, 0.03):
        _geom(b, None, S, (0.011,), (-0.078, y, face_z + 0.015), (0.05, 0.05, 0.05, 1), **nc)
    _geom(b, None, B, (0.005, 0.025, 0.006), (-0.08, 0, face_z - 0.035), (0.6, 0.25, 0.25, 1), **nc)
    return b


def build(volts="12V", objects=True, person=True) -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(ensure_model()))
    configure_arm(spec, volts)
    w = spec.worldbody
    light = w.add_light()
    light.pos, light.dir, light.type = [0.3, -0.3, 2.0], [0, 0.2, -1], mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    _geom(w, "floor", P, (0, 0, 0.05), (0, 0, FLOOR_Z), (0.25, 0.27, 0.3, 1))
    # Mesa 90 x 100 cm (gris claro para no confundir al detector de piel)
    _geom(w, "table", B, (0.45, 0.5, 0.015), (0.3, 0, TABLE_Z - 0.015), (0.82, 0.83, 0.85, 1))
    for sx in (-0.13, 0.73):
        for sy in (-0.45, 0.45):
            _geom(w, None, B, (0.02, 0.02, (TABLE_Z - FLOOR_Z) / 2 - 0.015),
                  (sx, sy, (TABLE_Z + FLOOR_Z) / 2 - 0.015), (0.4, 0.4, 0.42, 1))
    # Pared al fondo
    _geom(w, "wall", B, (0.02, 2.0, 1.2), (2.2, 0, FLOOR_Z + 1.2), (0.55, 0.62, 0.7, 1))

    if objects:
        # Cubo verde de 4 x 4 x 6 cm (30 g), pelota roja y lata azul
        for name, gtype, size, pos, rgba, mass in [
            ("cube", B, (0.02, 0.02, 0.03), (0.24, 0.0, 0.03), (0.1, 0.75, 0.2, 1), 0.03),
            ("ball", S, (0.022,), (0.22, 0.16, 0.022), (0.85, 0.1, 0.1, 1), 0.04),
            ("can", C, (0.02, 0.04), (0.2, -0.16, 0.04), (0.15, 0.3, 0.85, 1), 0.06),
        ]:
            b = w.add_body()
            b.name, b.pos = name, list(pos)
            b.add_freejoint()
            _geom(b, name, gtype, size, rgba=rgba, mass=mass, condim=4, friction=[1.0, 0.03, 0.003],
                  solref=[0.01, 1])

    if person:
        # Persona sentada al otro lado de la mesa (cuerpo "mocap": la movemos nosotros)
        add_person(w, "person", [0.95, 0.0, 0.0], mocap=True)

    # Cámara externa fija para los videos
    target = w.add_body()
    target.name, target.pos = "view_target", [0.5, 0.05, 0.12]
    cam = w.add_camera()
    cam.name, cam.pos = "side", [-0.35, -1.25, 0.6]
    cam.mode = mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY
    cam.targetbody = "view_target"
    return spec.compile()


def arm_ids(model):
    """Índices en qpos/qvel/ctrl de las 5 articulaciones del brazo y de la pinza."""
    j = [model.joint(n).id for n in ARM_JOINTS]
    qadr = np.array([model.jnt_qposadr[i] for i in j])
    dadr = np.array([model.jnt_dofadr[i] for i in j])
    act = np.array([model.actuator(n).id for n in ARM_JOINTS])
    g = model.joint(GRIPPER).id
    return qadr, dadr, act, model.jnt_qposadr[g], model.actuator(GRIPPER).id
