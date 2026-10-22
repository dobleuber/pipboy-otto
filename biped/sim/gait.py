"""Caminata programada (sin IA) con cinemática inversa de las piernas.

Sirve para Mini13 (5 motores por pierna) y Mini16 (6, con tobillo roll).

Idea:
  1. El cuerpo se balancea de lado a lado (cadera roll) para cargar el peso en un pie.
     Si hay tobillo roll, compensa para que los pies queden planos.
  2. El pie libre se levanta (rodilla) y se adelanta (cadera pitch); el de apoyo
     va hacia atrás, empujando el cuerpo hacia adelante.
  3. El tobillo pitch mantiene los pies paralelos al cuerpo.
  4. Para girar, da pasos más cortos de un lado y rota la cadera yaw.
  5. La cabeza compensa la inclinación del cuerpo (como las aves) y mira alrededor.

Orden de actuadores (igual que en los XML):
  pierna izquierda, pierna derecha (hip_yaw, hip_roll, hip_pitch, knee, ankle[, ankle_roll]),
  luego cabeza (neck_pitch, head_pitch, head_yaw[, head_roll]).
"""

from dataclasses import dataclass, fields, replace

import numpy as np

import robots


@dataclass
class GaitParams:
    """Los campos en None toman el valor por defecto del robot (robots.py)."""

    robot: str = None  # "mini13" / "mini16" (None = robots.DEFAULT)
    freq: float = None  # ciclos por segundo (cada ciclo = un paso con cada pie)
    step_len: float = None  # m, mitad del recorrido del pie hacia adelante/atrás
    lift: float = None  # m, altura a la que se levanta el pie
    sway: float = None  # m, balanceo lateral del cuerpo
    sway_lead: float = None  # rad, adelanto del balanceo respecto del paso
    hip_height: float = None  # m, altura de la cadera sobre la suela (rodillas flexionadas)
    foot_x: float = None  # m, posición del pie respecto de la cadera
    turn: float = 0.0  # giro (+ = izquierda). Con steer: velocidad de giro pedida en rad/s
    steer: bool = True  # corrige el rumbo con la IMU (si no, el giro es en lazo abierto)
    steer_gain: float = None  # ganancia del control de rumbo (por rad de error)
    steer_damping: float = None  # amortiguación (por rad/s de velocidad de giro, giroscopio)
    turn_yaw: float = None  # rad de cadera yaw por paso cuando turn = 1
    stride_bias: float = None  # corrige desvíos al caminar recto (pasos desiguales)
    ramp_time: float = 1.5  # s, arranque suave
    head: bool = True  # animar cabeza

    def __post_init__(self):
        rb = robots.get(self.robot)
        self.robot = rb.name
        for f in fields(self):
            if getattr(self, f.name) is None and f.name in rb.gait:
                setattr(self, f.name, rb.gait[f.name])

    @property
    def rb(self):
        return robots.get(self.robot)


def leg_ik(x: float, y: float, z: float, robot=None) -> np.ndarray:
    """Ángulos (hip_roll, hip_pitch, knee, ankle) para llevar el tobillo a (x, y, z).

    (x, y, z) se mide desde el eje de cadera pitch con roll = 0, en el marco del torso.
    La rodilla se dobla hacia atrás (como el Microduck) y el tobillo se elige para
    que el pie quede paralelo al torso en pitch.
    """
    rb = robots.get(robot)
    L1, L2, rp = rb.thigh, rb.shin, rb.roll_to_pitch
    pz = z - rp  # relativo al eje roll
    roll = np.arctan2(y, -pz)
    h = np.hypot(y, pz) - rp  # distancia hacia abajo en el plano de la pierna
    r = min(np.hypot(x, h), L1 + L2 - 1e-4)
    cos_knee = (L1**2 + L2**2 - r**2) / (2 * L1 * L2)
    knee = -(np.pi - np.arccos(np.clip(cos_knee, -1, 1)))
    alpha = np.arctan2(x, h)
    beta = np.arccos(np.clip((L1**2 + r**2 - L2**2) / (2 * L1 * r), -1, 1))
    hip_pitch = -alpha + beta
    ankle = -(hip_pitch + knee)
    return np.array([roll, hip_pitch, knee, ankle])


def leg_targets(t: float, p: GaitParams):
    """Posición del tobillo de cada pie (relativa a su cadera) y yaw de cadera."""
    ramp = min(1.0, t / p.ramp_time) if p.ramp_time > 0 else 1.0
    phi = 2 * np.pi * p.freq * t
    z0 = -(p.hip_height - p.rb.ankle_to_sole)

    # Pie izquierdo en el aire cuando sin(phi) > 0, derecho cuando sin(phi) < 0.
    swing_l = max(0.0, np.sin(phi)) ** 2  # perfil suave (sin golpes)
    swing_r = max(0.0, -np.sin(phi)) ** 2
    # Girar: pasos más cortos del lado hacia el que se gira (como un tanque).
    # Límite ±0.4: más allá los servos no alcanzan la velocidad necesaria.
    k = np.clip(p.turn + p.stride_bias, -0.4, 0.4)
    x_l = p.foot_x - p.step_len * (1 - k) * ramp * np.cos(phi)
    x_r = p.foot_x + p.step_len * (1 + k) * ramp * np.cos(phi)
    # Balanceo: el cuerpo se mueve hacia el pie de apoyo (los pies se mueven al revés).
    sway = p.sway * ramp * np.sin(phi + p.sway_lead)
    z_l = z0 + p.lift * ramp * swing_l
    z_r = z0 + p.lift * ramp * swing_r
    # Giro: la cadera yaw rota durante el paso, igual que x.
    yaw_l = -p.turn * p.turn_yaw * ramp * np.cos(phi) / 2
    yaw_r = p.turn * p.turn_yaw * ramp * np.cos(phi) / 2
    return (x_l, sway, z_l, yaw_l), (x_r, sway, z_r, yaw_r)


def leg_command(yaw, x, y, z, rb) -> list:
    roll, pitch, knee, ankle = leg_ik(x, y, z, rb)
    q = [yaw, roll, pitch, knee, ankle]
    if rb.ankle_roll:
        q.append(-roll)  # tobillo roll = -cadera roll: pie plano
    return q


def targets(t: float, p: GaitParams, torso_pitch: float = 0.0, torso_roll: float = 0.0) -> np.ndarray:
    """Ángulos objetivo de todos los motores en el tiempo t."""
    rb = p.rb
    (xl, yl, zl, yawl), (xr, yr, zr, yawr) = leg_targets(t, p)
    q = np.zeros(rb.n_act)
    q[: rb.per_leg] = leg_command(yawl, xl, yl, zl, rb)
    q[rb.per_leg : rb.n_leg] = leg_command(yawr, xr, yr, zr, rb)
    if p.head:
        q[rb.n_leg :] = head_targets(t, torso_pitch, torso_roll, rb.n_head)
    return q


def head_targets(t: float, torso_pitch: float, torso_roll: float, n_head: int = 3) -> np.ndarray:
    """Cabeza: compensa la inclinación del cuerpo y mira a los lados."""
    neck_pitch = 0.15 * np.sin(2 * np.pi * 0.3 * t)
    head_pitch = -torso_pitch - neck_pitch  # mantiene la mirada horizontal
    head_yaw = 0.6 * np.sin(2 * np.pi * 0.15 * t)
    q = [neck_pitch, head_pitch, head_yaw, -torso_roll]  # cabeza roll compensa el balanceo
    return np.array(q[:n_head])


class Steering:
    """Control de rumbo con la IMU (el BNO055 da el rumbo absoluto).

    Lleva un rumbo de referencia que avanza a la velocidad de giro pedida
    (params.turn, rad/s) y ajusta el giro de la caminata (pasos desiguales +
    cadera yaw) para seguirlo. Con turn = 0 mantiene la dirección inicial.
    """

    MAX_TURN = 0.35

    def __init__(self, params: GaitParams):
        self.params = params
        self.yaw_ref = 0.0
        self.prev_yaw = None
        self.rate = 0.0

    def update(self, yaw_measured: float, dt: float) -> GaitParams:
        p = self.params
        if not p.steer:
            return p
        if self.prev_yaw is not None:  # velocidad de giro filtrada (en el robot: giroscopio)
            self.rate += 0.2 * ((yaw_measured - self.prev_yaw) / dt - self.rate)
        self.prev_yaw = yaw_measured
        self.yaw_ref += p.turn * dt
        err = self.yaw_ref - yaw_measured
        u = p.steer_gain * err - p.steer_damping * (self.rate - p.turn) + 0.3 * p.turn
        turn_cmd = float(np.clip(u, -self.MAX_TURN, self.MAX_TURN))
        return replace(p, turn=turn_cmd, steer=False)
