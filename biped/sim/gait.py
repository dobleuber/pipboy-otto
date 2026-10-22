"""Caminata abierta (sin IA) tipo "pato" para Biped6.

Idea:
  1. Los dos tobillos roll inclinan el cuerpo hacia un lado -> el otro pie se levanta.
  2. Mientras un pie está en el aire, la cadera pitch lo adelanta.
  3. El tobillo pitch compensa la cadera para que los pies queden paralelos al torso
     (así el pie de apoyo queda plano en el piso y el torso derecho).

Orden de actuadores (igual que en model/biped6.xml):
  0 left_hip_pitch, 1 left_ankle_pitch, 2 left_ankle_roll,
  3 right_hip_pitch, 4 right_ankle_pitch, 5 right_ankle_roll
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class GaitParams:
    freq: float = 1.6  # pasos completos (izq + der) por segundo
    roll_amp: float = 0.15  # rad, inclinación lateral con los tobillos
    step_amp: float = 0.20  # rad, cuánto adelanta la cadera cada pierna
    phase: float = -np.pi / 2  # desfase entre inclinación y paso
    ramp_time: float = 1.5  # s, arranque suave
    turn: float = 0.0  # -1..1, diferencia de paso entre piernas para girar


def targets(t: float, p: GaitParams) -> np.ndarray:
    """Ángulos objetivo de los 6 servos en el tiempo t."""
    ramp = min(1.0, t / p.ramp_time) if p.ramp_time > 0 else 1.0
    phi = 2 * np.pi * p.freq * t

    roll = p.roll_amp * ramp * np.sin(phi)
    swing = p.step_amp * ramp * np.sin(phi + p.phase)

    left_hip = swing * (1 + p.turn)
    right_hip = -swing * (1 - p.turn)

    return np.array(
        [
            left_hip,
            -left_hip,  # pie izquierdo paralelo al torso
            roll,
            right_hip,
            -right_hip,  # pie derecho paralelo al torso
            roll,
        ]
    )
