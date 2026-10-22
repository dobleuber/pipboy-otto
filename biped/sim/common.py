"""Utilidades compartidas: cargar el modelo y simular la caminata."""

from pathlib import Path

import mujoco
import numpy as np

from gait import N_LEG, GaitParams, targets

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


def torso_pitch_roll(data):
    """Pitch y roll del torso (rad), como los mediría la IMU."""
    R = data.xmat[1].reshape(3, 3)
    pitch = float(np.arcsin(np.clip(-R[2, 0], -1, 1)))
    roll = float(np.arctan2(R[2, 1], R[2, 2]))
    return pitch, roll


def fallen(data) -> bool:
    return data.qpos[2] < 0.05 or torso_tilt(data) > 0.8


def yaw(data) -> float:
    R = data.xmat[1].reshape(3, 3)
    return float(np.arctan2(R[1, 0], R[0, 0]))


def simulate(params: GaitParams, seconds: float, on_frame=None, load_fn=None):
    """Corre la caminata. Devuelve métricas. on_frame(model, data) se llama a 30 fps."""
    model, data = (load_fn or load)()
    steps_per_ctrl = int(round(1 / (CONTROL_HZ * model.opt.timestep)))
    frame_every = int(round(1 / (30 * model.opt.timestep)))
    n = int(seconds / model.opt.timestep)
    max_tilt = 0.0
    max_torque = 0.0
    torques, errors = [], []
    prev_ctrl, max_cmd_vel = None, 0.0
    yaw_total, prev_yaw = 0.0, yaw(data)
    fell_at = None
    for i in range(n):
        if i % steps_per_ctrl == 0:
            pitch, roll = torso_pitch_roll(data)
            data.ctrl[:] = targets(data.time, params, pitch, roll)
            if prev_ctrl is not None and data.time > 0.5:
                vel = np.abs(data.ctrl[:N_LEG] - prev_ctrl) * CONTROL_HZ
                max_cmd_vel = max(max_cmd_vel, float(vel.max()))
            prev_ctrl = data.ctrl[:N_LEG].copy()
            y = yaw(data)
            yaw_total += (y - prev_yaw + np.pi) % (2 * np.pi) - np.pi  # giro acumulado
            prev_yaw = y
        mujoco.mj_step(model, data)
        max_tilt = max(max_tilt, torso_tilt(data))
        max_torque = max(max_torque, float(np.abs(data.actuator_force[:N_LEG]).max()))
        if data.time > 2.0 and i % 5 == 0:
            torques.append(np.abs(data.actuator_force[:N_LEG]))
            errors.append(np.abs(data.ctrl[:N_LEG] - data.qpos[7 : 7 + N_LEG]))
        if on_frame is not None and i % frame_every == 0:
            on_frame(model, data)
        if fell_at is None and fallen(data):
            fell_at = data.time
            if on_frame is None:
                break
    return {
        "x": float(data.qpos[0]),
        "y": float(data.qpos[1]),
        "yaw_deg": float(np.degrees(yaw_total)),
        "fell_at": fell_at,
        "max_tilt_deg": float(np.degrees(max_tilt)),
        "max_leg_torque": max_torque,
        # Percentil 99: torque de pierna (N·m) y error de seguimiento (grados)
        "p99_leg_torque": float(np.percentile(torques, 99)) if torques else 0.0,
        "p99_track_err_deg": float(np.degrees(np.percentile(errors, 99))) if errors else 0.0,
        # Velocidad máxima pedida a un servo de pierna (rad/s); STS3215 ~4.7 rad/s sin carga
        "max_cmd_vel": max_cmd_vel,
        "time": float(data.time),
    }
