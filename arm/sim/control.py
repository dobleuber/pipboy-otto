"""Control del brazo: cinemática inversa, seguimiento con la cámara y detector de caras.

Todo lo que usa el seguimiento lo tendría el robot real: la imagen de la cámara de muñeca y los
ángulos de los servos. No usa la posición "verdadera" de la persona.
"""

import mujoco
import numpy as np

from scene import SKIN, arm_ids

CONTROL_HZ = 25
MAX_SPEED = 2.0  # rad/s por articulación (el STS3215 llega a ~4.7 sin carga)
MAX_ACCEL = 10.0  # rad/s² (arranques y frenadas suaves: menos golpes de torque)
REST = np.array([0.0, -0.9, 0.9, -0.7, -1.57])  # postura cómoda (cámara derecha, mirando adelante)


class Arm:
    """Lleva los objetivos de los servos y los mueve suavemente (a velocidad limitada)."""

    def __init__(self, model, data):
        self.m, self.d = model, data
        self.qadr, self.dadr, self.act, self.gq, self.gact = arm_ids(model)
        self.lo, self.hi = model.jnt_range[[model.jnt_qposadr.tolist().index(a) for a in self.qadr]].T
        self.q_cmd = data.qpos[self.qadr].copy()
        self.dq = np.zeros(len(self.qadr))
        self.grip_cmd = float(data.qpos[self.gq])
        self.substeps = int(round(1 / (CONTROL_HZ * model.opt.timestep)))
        self.site = model.site("gripperframe").id
        self.gripper_body = model.body("gripper").id
        self.cam = model.camera("wrist_cam").id

    def set_pose(self, q):
        self.d.qpos[self.qadr] = q
        self.q_cmd = np.array(q, float)
        self.dq = np.zeros(len(self.qadr))
        self.d.ctrl[self.act] = q
        mujoco.mj_forward(self.m, self.d)

    def move(self, dq):
        """Aplica una velocidad (rad/s) por un paso de control."""
        dq = np.clip(dq, -MAX_SPEED, MAX_SPEED)
        dv = MAX_ACCEL / CONTROL_HZ
        dq = np.clip(dq, self.dq - dv, self.dq + dv)
        self.dq = dq
        self.q_cmd = np.clip(self.q_cmd + dq / CONTROL_HZ, self.lo + 0.02, self.hi - 0.02)

    def step(self, on_substep=None):
        # Interpola el objetivo dentro del paso de control (como el perfil de velocidad del servo)
        start = self.d.ctrl[self.act].copy()
        self.d.ctrl[self.gact] = self.grip_cmd
        for i in range(self.substeps):
            self.d.ctrl[self.act] = start + (self.q_cmd - start) * (i + 1) / self.substeps
            mujoco.mj_step(self.m, self.d)
            if on_substep:
                on_substep()

    # ------------------------------------------------------------- cinemática
    def jac(self, body=None, point=None):
        jp = np.zeros((3, self.m.nv))
        jr = np.zeros((3, self.m.nv))
        if point is None:
            mujoco.mj_jacSite(self.m, self.d, jp, jr, self.site)
        else:
            mujoco.mj_jac(self.m, self.d, jp, jr, point, body)
        return jp[:, self.dadr], jr[:, self.dadr]

    def site_pose(self):
        return self.d.site_xpos[self.site].copy(), self.d.site_xmat[self.site].reshape(3, 3).copy()

    def cam_frame(self):
        return self.d.cam_xpos[self.cam].copy(), self.d.cam_xmat[self.cam].reshape(3, 3).copy()


def dls(J, err, lam=0.05):
    """Mínimos cuadrados amortiguados: dq tal que J dq ≈ err."""
    return J.T @ np.linalg.solve(J @ J.T + lam**2 * np.eye(J.shape[0]), err)


def nullspace(J, lam=0.05):
    Jp = J.T @ np.linalg.inv(J @ J.T + lam**2 * np.eye(J.shape[0]))
    return np.eye(J.shape[1]) - Jp @ J


def reach_velocity(arm, target, approach=None, gain=4.0, posture_gain=0.5):
    """Velocidad articular para llevar la pinza a `target` (y su eje x hacia `approach`)."""
    p, R = arm.site_pose()
    jp, jr = arm.jac()
    err = gain * (np.asarray(target) - p)
    J = jp
    if approach is not None:
        a = R[:, 0]
        rot_err = np.cross(a, approach / np.linalg.norm(approach))  # gira el eje x hacia approach
        err = np.concatenate([err, gain * rot_err])
        J = np.vstack([jp, jr])
    dq = dls(J, err)
    q = arm.d.qpos[arm.qadr]
    dq += nullspace(J) @ (posture_gain * (REST - q))
    return dq, float(np.linalg.norm(np.asarray(target) - p))


# ------------------------------------------------------------------ visión
def detect_face(img):
    """Busca piel en la imagen (como un detector de caras simple). Devuelve (u, v, tamaño) o None.

    u, v en [-1, 1] (derecha y abajo positivos); tamaño = fracción de la imagen ocupada.
    """
    f = img.astype(np.float32) / 255.0
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    tr, tg, tb = SKIN[:3]
    mask = (r > 0.25) & (np.abs(g / (r + 1e-6) - tg / tr) < 0.1) & (np.abs(b / (r + 1e-6) - tb / tr) < 0.12)
    n = int(mask.sum())
    if n < 12:
        return None
    ys, xs = np.nonzero(mask)
    H, W = mask.shape
    return (xs.mean() / W * 2 - 1, ys.mean() / H * 2 - 1, n / mask.size)


def ray_world(arm, u, v, fovy_deg=61.0, aspect=4 / 3):
    """Dirección (marco mundo) del punto visto en (u, v) de la imagen."""
    _, Rc = arm.cam_frame()
    th = np.tan(np.radians(fovy_deg) / 2)
    r = np.array([u * th * aspect, -v * th, -1.0])
    return Rc @ (r / np.linalg.norm(r))


class TargetMotion:
    """Estima la velocidad angular del objetivo visto (rad/s, mundo) con detecciones seguidas.

    Sirve para adelantarse cuando el objetivo (o uno mismo) se mueve: sin esto, el seguimiento
    va siempre un poco atrasado.
    """

    def __init__(self, dt, smooth=0.3):
        self.dt, self.smooth = dt, smooth
        self.prev, self.omega = None, np.zeros(3)

    def update(self, ray):
        if ray is None:
            self.prev, self.omega = None, np.zeros(3)
            return self.omega
        if self.prev is not None:
            w = np.cross(self.prev, ray) / self.dt
            self.omega = (1 - self.smooth) * self.omega + self.smooth * w
        self.prev = ray
        return self.omega


def look_velocity(arm, u, v, gain=2.5, posture_gain=0.6, fovy_deg=61.0, aspect=4 / 3, base_omega=None,
                  target_omega=None):
    """Velocidad articular para centrar en la imagen un punto visto en (u, v), con la cámara derecha.

    Gira la cámara alrededor de sus ejes (servo visual por imagen) y mantiene el horizonte
    nivelado (sin roll). La postura sobrante vuelve a REST. Si la base se mueve (brazo en el
    morral), base_omega = velocidad angular de la base medida por la IMU (rad/s, marco mundo).
    """
    _, Rc = arm.cam_frame()  # columnas: x derecha, y arriba, z hacia atrás (MuJoCo)
    half_v = np.radians(fovy_deg) / 2
    half_h = np.arctan(np.tan(half_v) * aspect)
    # Ángulos al objetivo en el marco de la cámara
    yaw_err = -np.arctan(u * np.tan(half_h))  # objetivo a la derecha -> girar a la derecha (-y)
    pitch_err = -np.arctan(v * np.tan(half_v))  # objetivo abajo -> bajar la mirada (-x)
    roll_err = -Rc[2, 0]  # eje x de la cámara debería quedar horizontal
    w_cam = gain * np.array([pitch_err, yaw_err, roll_err])
    w = Rc @ w_cam
    if target_omega is not None:
        w = w + target_omega  # adelantarse al movimiento del objetivo
    if base_omega is not None:
        # La base gira (IMU): los servos compensan ese giro para que la cámara no se sacuda
        w = w - base_omega
    _, jr = arm.jac()
    dq = dls(jr, w)
    q = arm.d.qpos[arm.qadr]
    dq += nullspace(jr) @ (posture_gain * (REST - q))
    return dq
