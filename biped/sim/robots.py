"""Robots disponibles y sus datos geométricos.

Elegir robot: variable de entorno MINI_ROBOT (mini13 por defecto) o pasar `robot=`
a las funciones. Ej.: MINI_ROBOT=mini17 python run_demo.py
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"


@dataclass(frozen=True)
class Robot:
    name: str
    scene: Path
    # Geometría de la pierna (debe coincidir con el XML)
    roll_to_pitch: float  # m, del eje roll al eje pitch de la cadera
    thigh: float  # m
    shin: float  # m
    ankle_to_sole: float  # m
    ankle_roll: bool  # True si tiene tobillo roll (6 motores por pierna)
    n_head: int  # motores de cuello/cabeza
    gait: dict = field(default_factory=dict)  # parámetros de caminata por defecto
    target_speed: float = 0.06  # m/s, velocidad objetivo para el entrenamiento con IA

    @property
    def leg_joints(self):
        j = ["hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle"]
        return j + ["ankle_roll"] if self.ankle_roll else j

    @property
    def per_leg(self):
        return len(self.leg_joints)

    @property
    def n_leg(self):
        return 2 * self.per_leg

    @property
    def n_act(self):
        return self.n_leg + self.n_head


ROBOTS = {
    "mini13": Robot(
        name="mini13",
        scene=MODEL_DIR / "scene_mini13.xml",
        roll_to_pitch=0.014,
        thigh=0.055,
        shin=0.06,
        ankle_to_sole=0.025,
        ankle_roll=False,
        n_head=3,
        target_speed=0.06,
        gait=dict(freq=1.6, step_len=0.016, lift=0.008, sway=0.002, sway_lead=0.0, hip_height=0.115,
                  foot_x=0.0, turn_yaw=0.0, stride_bias=0.0, steer_gain=0.2, steer_damping=0.0),
    ),
    "mini17": Robot(
        name="mini17",
        scene=MODEL_DIR / "scene_mini17.xml",
        roll_to_pitch=0.012,
        thigh=0.04,
        shin=0.045,
        ankle_to_sole=0.02,
        ankle_roll=True,
        n_head=5,
        gait=dict(freq=1.2, step_len=0.01, lift=0.02, sway=0.025, sway_lead=0.0, hip_height=0.085,
                  foot_x=-0.008, turn_yaw=0.4, stride_bias=0.0, steer_gain=0.3, steer_damping=0.0),
    ),
}

DEFAULT = os.environ.get("MINI_ROBOT", "mini13")


def get(name=None) -> Robot:
    if isinstance(name, Robot):
        return name
    return ROBOTS[name or DEFAULT]
