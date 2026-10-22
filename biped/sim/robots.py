"""Robots disponibles y sus datos geométricos.

Elegir robot: variable de entorno MINI_ROBOT (mini16 por defecto) o pasar `robot=`
a las funciones. Ej.: MINI_ROBOT=mini13 python run_demo.py
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
    rl_log_std: float = -1.5  # ruido inicial de exploración de la IA (log de la desviación)
    servo_speed: float = 4.7  # rad/s, velocidad máxima del servo de pierna (STS3215 sin carga)
    rl_head: bool = False  # True: la IA también mueve cuello y cabeza (contrapeso)

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
        rl_log_std=-2.5,  # sin tobillo roll es más inestable: explorar con menos ruido
        gait=dict(freq=1.6, step_len=0.016, lift=0.008, sway=0.002, sway_lead=0.0, hip_height=0.115,
                  foot_x=0.0, turn_yaw=0.0, stride_bias=0.0, steer_gain=0.2, steer_damping=0.0),
    ),
    "mini16": Robot(
        # Geometría generada desde el CAD (cad/lib/params.scad, cad/build_mjcf.py)
        name="mini16",
        scene=MODEL_DIR / "scene_mini16.xml",
        roll_to_pitch=0.02822,
        thigh=0.03333,
        shin=0.03333,
        ankle_to_sole=0.03333 + 0.0345,  # tobillo pitch -> tobillo roll -> suela
        ankle_roll=True,
        n_head=4,
        gait=dict(freq=1.5, step_len=0.008, lift=0.006, sway=0.014, sway_lead=0.0, hip_height=0.12,
                  foot_x=-0.02, turn_yaw=0.4, stride_bias=0.0, steer_gain=0.3, steer_damping=0.0),
    ),
    "mini14": Robot(
        # Diseño nuevo con lo aprendido del Microduck (model/build_mini14.py, LECCIONES.md)
        name="mini14",
        scene=MODEL_DIR / "scene_mini14.xml",
        roll_to_pitch=0.024,
        thigh=0.045,
        shin=0.045,
        ankle_to_sole=0.022,
        ankle_roll=False,
        n_head=4,
        target_speed=0.08,
        rl_log_std=-2.0,
        servo_speed=10.0,  # XL330-M288 a 7.4 V (~16 rad/s sin carga; margen por carga)
        rl_head=True,
        # Servos blandos: la referencia corrige la inclinación con el tobillo (balance) y casi no
        # avanza sola; avanzar es lo que aprende la IA.
        gait=dict(freq=2.0, step_len=0.008, lift=0.009, sway=0.0, sway_lead=0.0, hip_height=0.1,
                  foot_x=0.0, turn_yaw=0.3, stride_bias=0.0, steer_gain=0.2, steer_damping=0.0,
                  balance=0.6),
    ),
}

DEFAULT = os.environ.get("MINI_ROBOT", "mini16")


def get(name=None) -> Robot:
    if isinstance(name, Robot):
        return name
    return ROBOTS[name or DEFAULT]
