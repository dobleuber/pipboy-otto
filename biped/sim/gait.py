"""Caminata programada (sin IA) para Mini15, con cinemática inversa de las piernas.

Idea:
  1. El cuerpo se balancea de lado a lado (cadera roll) para cargar el peso en un pie.
  2. El pie libre se levanta (rodilla) y se adelanta (cadera pitch); el de apoyo
     va hacia atrás, empujando el cuerpo hacia adelante.
  3. El tobillo mantiene los pies paralelos al cuerpo.
  4. Para girar, da pasos más cortos de un lado y rota un poco la cadera yaw.
  5. La cabeza compensa la inclinación del cuerpo (como las aves) y mira alrededor.

Orden de actuadores (igual que en model/mini15.xml):
   0-4  pierna izquierda: hip_yaw, hip_roll, hip_pitch, knee, ankle
   5-9  pierna derecha:   hip_yaw, hip_roll, hip_pitch, knee, ankle
  10-14 cabeza:           neck_pitch, head_pitch, head_yaw, head_roll, jaw
"""

from dataclasses import dataclass

import numpy as np

# Geometría de la pierna (debe coincidir con patito.xml)
ROLL_TO_PITCH = 0.012  # m, del eje roll al eje pitch de la cadera
THIGH = 0.04  # m
SHIN = 0.045  # m
ANKLE_TO_SOLE = 0.02  # m

N_ACT = 15


@dataclass
class GaitParams:
    freq: float = 2.0  # ciclos por segundo (cada ciclo = un paso con cada pie)
    step_len: float = 0.012  # m, mitad del recorrido del pie hacia adelante/atrás
    lift: float = 0.005  # m, altura a la que se levanta el pie
    sway: float = 0.002  # m, balanceo lateral del cuerpo
    sway_lead: float = 0.6  # rad, adelanto del balanceo respecto del paso
    hip_height: float = 0.085  # m, altura de la cadera sobre la suela (rodillas flexionadas)
    foot_x: float = 0.0  # m, posición del pie respecto de la cadera
    turn: float = 0.0  # -0.35..0.35: giro (+ = izquierda). Pasos desiguales + cadera yaw
    turn_yaw: float = 0.15  # rad de cadera yaw por paso cuando turn = 1
    stride_bias: float = 0.04  # corrige el desvío natural al caminar recto
    ramp_time: float = 1.5  # s, arranque suave
    head: bool = True  # animar cabeza y boca


def leg_ik(x: float, y: float, z: float) -> np.ndarray:
    """Ángulos (hip_roll, hip_pitch, knee, ankle) para llevar el tobillo a (x, y, z).

    (x, y, z) se mide desde el eje de cadera pitch con roll = 0, en el marco del torso.
    La rodilla se dobla hacia atrás (como el Microduck) y el tobillo se elige para
    que el pie quede paralelo al torso.
    """
    pz = z - ROLL_TO_PITCH  # relativo al eje roll
    roll = np.arctan2(y, -pz)
    h = np.hypot(y, pz) - ROLL_TO_PITCH  # distancia hacia abajo en el plano de la pierna
    r = min(np.hypot(x, h), THIGH + SHIN - 1e-4)
    cos_knee = (THIGH**2 + SHIN**2 - r**2) / (2 * THIGH * SHIN)
    knee = -(np.pi - np.arccos(np.clip(cos_knee, -1, 1)))
    alpha = np.arctan2(x, h)
    beta = np.arccos(np.clip((THIGH**2 + r**2 - SHIN**2) / (2 * THIGH * r), -1, 1))
    hip_pitch = -alpha + beta
    ankle = -(hip_pitch + knee)
    return np.array([roll, hip_pitch, knee, ankle])


def leg_targets(t: float, p: GaitParams):
    """Posición del tobillo de cada pie (relativa a su cadera) y yaw de cadera."""
    ramp = min(1.0, t / p.ramp_time) if p.ramp_time > 0 else 1.0
    phi = 2 * np.pi * p.freq * t
    z0 = -(p.hip_height - ANKLE_TO_SOLE)

    # Pie izquierdo en el aire cuando sin(phi) > 0, derecho cuando sin(phi) < 0.
    swing_l = max(0.0, np.sin(phi)) ** 2  # perfil suave (sin golpes)
    swing_r = max(0.0, -np.sin(phi)) ** 2
    # Adelante/atrás: el pie en el aire va de atrás hacia adelante.
    # Girar: pasos más cortos del lado hacia el que se gira (como un tanque).
    # Límite ±0.4: más allá los servos no alcanzan la velocidad necesaria.
    k = np.clip(p.turn + p.stride_bias, -0.4, 0.4)
    x_l = p.foot_x - p.step_len * (1 - k) * ramp * np.cos(phi)
    x_r = p.foot_x + p.step_len * (1 + k) * ramp * np.cos(phi)
    # Balanceo: el cuerpo se mueve hacia el pie de apoyo (los pies se mueven al revés).
    sway = p.sway * ramp * np.sin(phi + p.sway_lead)
    y_l = sway
    y_r = sway
    z_l = z0 + p.lift * ramp * swing_l
    z_r = z0 + p.lift * ramp * swing_r
    # Giro: la cadera yaw rota durante el paso, igual que x.
    yaw_l = -p.turn * p.turn_yaw * ramp * np.cos(phi) / 2
    yaw_r = p.turn * p.turn_yaw * ramp * np.cos(phi) / 2
    return (x_l, y_l, z_l, yaw_l), (x_r, y_r, z_r, yaw_r)


def targets(t: float, p: GaitParams, torso_pitch: float = 0.0, torso_roll: float = 0.0) -> np.ndarray:
    """Ángulos objetivo de los 15 motores en el tiempo t."""
    (xl, yl, zl, yawl), (xr, yr, zr, yawr) = leg_targets(t, p)
    q = np.zeros(N_ACT)
    q[0] = yawl
    q[1:5] = leg_ik(xl, yl, zl)
    q[5] = yawr
    q[6:10] = leg_ik(xr, yr, zr)
    if p.head:
        q[10:15] = head_targets(t, torso_pitch, torso_roll)
    return q


def head_targets(t: float, torso_pitch: float, torso_roll: float) -> np.ndarray:
    """Cabeza: compensa la inclinación del cuerpo y mira a los lados; la boca se abre a ratos."""
    neck_pitch = 0.15 * np.sin(2 * np.pi * 0.3 * t)
    head_pitch = -torso_pitch - neck_pitch  # mantiene la mirada horizontal
    head_yaw = 0.6 * np.sin(2 * np.pi * 0.15 * t)
    head_roll = -torso_roll
    jaw = 0.5 if (t % 3.0) < 0.4 else 0.0  # abre la boca cada 3 s
    return np.array([neck_pitch, head_pitch, head_yaw, head_roll, jaw])
