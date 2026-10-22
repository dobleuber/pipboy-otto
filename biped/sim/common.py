"""Utilidades compartidas: cargar el modelo y simular la caminata."""

from pathlib import Path

import mujoco
import numpy as np

from gait import GaitParams, targets

SCENE = Path(__file__).resolve().parent.parent / "model" / "scene.xml"
CONTROL_HZ = 50  # igual que el Microduck / Open Duck


def load():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    return model, data


def torso_tilt(data) -> float:
    """Ángulo (rad) entre el eje vertical del torso y la vertical del mundo."""
    up_z = data.xmat[1].reshape(3, 3)[2, 2]
    return float(np.arccos(np.clip(up_z, -1, 1)))


def fallen(data) -> bool:
    return data.qpos[2] < 0.09 or torso_tilt(data) > 0.8


def simulate(params: GaitParams, seconds: float, on_frame=None):
    """Corre la caminata. Devuelve métricas. on_frame(model, data) se llama a 30 fps."""
    model, data = load()
    steps_per_ctrl = int(round(1 / (CONTROL_HZ * model.opt.timestep)))
    frame_every = int(round(1 / (30 * model.opt.timestep)))
    n = int(seconds / model.opt.timestep)
    max_tilt = 0.0
    fell_at = None
    for i in range(n):
        if i % steps_per_ctrl == 0:
            data.ctrl[:] = targets(data.time, params)
        mujoco.mj_step(model, data)
        max_tilt = max(max_tilt, torso_tilt(data))
        if on_frame is not None and i % frame_every == 0:
            on_frame(model, data)
        if fell_at is None and fallen(data):
            fell_at = data.time
            if on_frame is None:
                break
    return {
        "x": float(data.qpos[0]),
        "y": float(data.qpos[1]),
        "fell_at": fell_at,
        "max_tilt_deg": float(np.degrees(max_tilt)),
        "time": float(data.time),
    }
