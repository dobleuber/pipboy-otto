"""Entorno de entrenamiento (Gymnasium) para Mini13 / Mini17.

La IA no aprende a caminar desde cero: aprende CORRECCIONES sobre la caminata
programada (sim/gait.py). Esto acelera mucho el entrenamiento y hace que el
comportamiento inicial ya sea razonable.

La caminata de referencia incluye el control de rumbo con la IMU (gait.Steering).

Observación (todo lo puede medir el robot real):
  - gravedad en el marco del torso (IMU)          3
  - velocidad angular (IMU)                       3
  - posición de los motores de pierna             N_LEG (10 en Mini13, 12 en Mini17),
                                                  relativa a la caminata programada
  - velocidad de los motores de pierna            N_LEG
  - acción anterior                               N_LEG
  - fase de la caminata (sin, cos)                2
  - contacto de los pies                          2
  - distancia al piso delante (sensor ToF)        N_RAYS
Acción: N_LEG correcciones en [-1, 1] -> ±ACTION_SCALE rad sobre cada motor de pierna.

Variación aleatoria en cada episodio (para que funcione en el robot real):
fricción, peso extra, rigidez de los servos, retardo de control y empujones.
"""

import sys
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np

SIM = Path(__file__).resolve().parent.parent / "sim"
sys.path.insert(0, str(SIM))

import robots  # noqa: E402
from common import fallen, yaw  # noqa: E402
from gait import GaitParams, Steering, head_targets, targets  # noqa: E402

CONTROL_HZ = 50
ACTION_SCALE = 0.3  # rad
N_RAYS = 6
RAY_X = np.linspace(0.04, 0.14, N_RAYS)  # m delante del torso
MAX_SERVO_SPEED = 4.7  # rad/s (STS3215 sin carga)
START_X = 0.12  # distancia al obstáculo
TERRAIN_GROUP = 2  # grupo de geometrías del terreno (el sensor solo ve este grupo)
_RAY_GROUPS = np.array([0, 0, 1, 0, 0, 0], np.uint8)

# Terrenos: (tipo, valor). Rampas en grados, escalones en metros.
TERRAINS = {
    "flat": [("flat", 0)],
    "ramps": [("ramp", a) for a in (5, 10, 15, 20)],
    "steps": [("step", h) for h in (0.005, 0.01, 0.015, 0.02)],
}
TERRAINS["mix"] = TERRAINS["flat"] + TERRAINS["ramps"] + TERRAINS["steps"]


def _box(spec, name, pos, size, euler=(0, 0, 0)):
    g = spec.worldbody.add_geom()
    g.name, g.type = name, mujoco.mjtGeom.mjGEOM_BOX
    g.pos, g.size = pos, size
    q = np.zeros(4)
    mujoco.mju_euler2Quat(q, np.asarray(euler, float), "xyz")
    g.quat = q
    g.contype, g.conaffinity = 1, 2
    g.group = TERRAIN_GROUP
    g.rgba = [0.8, 0.65, 0.45, 1]


def build_model(kind, value, robot=None):
    spec = mujoco.MjSpec.from_file(str(robots.get(robot).scene))
    spec.geom("floor").group = TERRAIN_GROUP
    if kind == "ramp":
        th = np.radians(value)
        L, t = 0.5, 0.01
        _box(spec, "ramp", [START_X + L * np.cos(th) + t * np.sin(th), 0, L * np.sin(th) - t * np.cos(th)],
             [L, 0.4, t], (0, -th, 0))
        top, x_end = 2 * L * np.sin(th), START_X + 2 * L * np.cos(th)
        _box(spec, "ramp_top", [x_end + 0.5, 0, top / 2], [0.5, 0.4, top / 2])
    elif kind == "step":
        # Tres escalones seguidos, separados 25 cm.
        for i in range(3):
            _box(spec, f"step{i}", [START_X + 0.25 * i + 0.5, 0, (i + 1) * value / 2], [0.5 - 0.0, 0.4, (i + 1) * value / 2])
    return spec.compile()


class MiniEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 30}

    def __init__(self, terrain="mix", robot=None, episode_seconds=10.0, randomize=True, push=True,
                 target_speed=None, render_mode=None, seed=None):
        super().__init__()
        self.rb = robots.get(robot)
        self.n_leg = self.rb.n_leg
        self.terrain_list = TERRAINS[terrain] if isinstance(terrain, str) else list(terrain)
        self.models = {t: build_model(*t, self.rb) for t in self.terrain_list}
        self.base_torso_mass = float(next(iter(self.models.values())).body_mass[1])
        self.episode_steps = int(episode_seconds * CONTROL_HZ)
        self.randomize, self.push = randomize, push
        self.render_mode = render_mode
        self.gait = GaitParams(robot=self.rb.name)
        self.target_speed = target_speed or self.rb.target_speed
        self.rng = np.random.default_rng(seed)
        n_obs = 3 + 3 + self.n_leg * 3 + 2 + 2 + N_RAYS
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (n_obs,), np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (self.n_leg,), np.float32)
        self._renderer = None

    # ------------------------------------------------------------------ helpers
    def _setup(self, key):
        m = self.models[key]
        self.m, self.d = m, mujoco.MjData(m)
        self.substeps = int(round(1 / (CONTROL_HZ * m.opt.timestep)))
        self.leg_qadr = 7 + np.arange(self.n_leg)
        self.leg_dadr = 6 + np.arange(self.n_leg)
        self.imu = m.site("imu").id
        self.soles = [m.geom("left_sole").id, m.geom("right_sole").id]
        self.torso = m.body("torso").id
        self.lo, self.hi = m.actuator_ctrlrange[: self.n_leg].T

    def _randomize(self):
        m = self.m
        r = self.rng
        if not self.randomize:
            return
        fr = r.uniform(0.5, 1.3)
        for g in self.soles:
            m.geom_friction[g, 0] = fr
        m.body_mass[self.torso] = self.base_torso_mass + r.uniform(0, 0.15)
        kp = r.uniform(7, 15)
        m.actuator_gainprm[: self.n_leg, 0] = kp
        m.actuator_biasprm[: self.n_leg, 1] = -kp
        self.delay = int(r.integers(0, 2))  # 0 o 1 paso de control (0-20 ms)

    def _rays(self):
        """Distancia vertical del torso al piso en puntos delante (como un sensor ToF)."""
        d, m = self.d, self.m
        R = d.xmat[self.torso].reshape(3, 3)
        fwd = R[:, 0].copy()
        fwd[2] = 0
        fwd /= np.linalg.norm(fwd) + 1e-9
        base = d.xpos[self.torso]
        out = np.zeros(N_RAYS)
        geomid = np.zeros(1, np.int32)
        for i, dx in enumerate(RAY_X):
            p = base + fwd * dx + np.array([0, 0, 0.1])
            dist = mujoco.mj_ray(m, d, p, np.array([0, 0, -1.0]), _RAY_GROUPS, 1, -1, geomid)
            if dist < 0:
                dist = 0.3
            out[i] = dist - 0.1  # altura del torso sobre el piso en ese punto
        return out

    def _obs(self):
        d = self.d
        R = d.site_xmat[self.imu].reshape(3, 3)
        grav = R.T @ np.array([0, 0, -1.0])
        gyro = d.sensor("imu_gyro").data
        q = d.qpos[self.leg_qadr] - self.ref_q
        qd = d.qvel[self.leg_dadr]
        ph = 2 * np.pi * self.gait.freq * d.time
        contacts = np.array([self._foot_contact(g) for g in self.soles], float)
        rays = (self._rays() - 0.085) / 0.05
        obs = np.concatenate([grav, gyro * 0.25, q * 2.0, qd * 0.1, self.prev_action,
                              [np.sin(ph), np.cos(ph)], contacts, rays])
        return obs.astype(np.float32)

    def _foot_contact(self, gid):
        d = self.d
        for i in range(d.ncon):
            c = d.contact[i]
            if c.geom1 == gid or c.geom2 == gid:
                return 1.0
        return 0.0

    # --------------------------------------------------------------------- API
    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        key = self.terrain_list[int(self.rng.integers(len(self.terrain_list)))]
        if options and "terrain" in options:
            key = tuple(options["terrain"])
            if key not in self.models:
                self.models[key] = build_model(*key, self.rb)
        self.key = key
        self._setup(key)
        self.delay = 0
        self._randomize()
        mujoco.mj_resetDataKeyframe(self.m, self.d, 0)
        mujoco.mj_forward(self.m, self.d)
        self.t = 0
        self.prev_action = np.zeros(self.n_leg)
        self.pending = []
        self.ref_q = targets(0.0, self.gait)[: self.n_leg]
        self.push_at = self.rng.uniform(2, 6) if self.push else 1e9
        self.start_x = self.d.qpos[0]
        # La caminata de referencia mantiene el rumbo con la IMU (igual que en el robot real).
        self.steering = Steering(self.gait)
        self.yaw_total, self.prev_yaw = 0.0, yaw(self.d)
        return self._obs(), {"terrain": key}

    def step(self, action):
        action = np.clip(np.asarray(action, float), -1, 1)
        d, m = self.d, self.m
        y = yaw(d)
        self.yaw_total += (y - self.prev_yaw + np.pi) % (2 * np.pi) - np.pi
        self.prev_yaw = y
        full = targets(d.time, self.steering.update(self.yaw_total, 1 / CONTROL_HZ))
        self.ref_q = full[: self.n_leg]
        cmd = np.clip(self.ref_q + ACTION_SCALE * action, self.lo, self.hi)
        # Límite de velocidad del servo real
        prev_cmd = d.ctrl[: self.n_leg].copy()
        max_delta = MAX_SERVO_SPEED / CONTROL_HZ
        cmd = np.clip(cmd, prev_cmd - max_delta, prev_cmd + max_delta)
        self.pending.append(cmd)
        if len(self.pending) > self.delay:
            d.ctrl[: self.n_leg] = self.pending.pop(0)
        d.ctrl[self.n_leg :] = head_targets(d.time, 0.0, 0.0, self.rb.n_head)

        x0 = d.qpos[0]
        if self.push and abs(d.time - self.push_at) < 0.5 / CONTROL_HZ:
            d.xfrc_applied[self.torso, :2] = self.rng.uniform(-1.5, 1.5, 2)
        for _ in range(self.substeps):
            mujoco.mj_step(m, d)
        d.xfrc_applied[self.torso, :] = 0
        self.t += 1

        vx = (d.qpos[0] - x0) * CONTROL_HZ
        R = d.xmat[self.torso].reshape(3, 3)
        up = R[2, 2]
        yaw_rate = d.qvel[5]
        tau = d.actuator_force[: self.n_leg]
        r_vel = np.exp(-((vx - self.target_speed) / 0.04) ** 2) + 2.0 * min(vx, self.target_speed)
        r_up = -2.0 * (1 - up)
        r_smooth = -0.02 * np.sum((action - self.prev_action) ** 2)
        r_torque = -0.002 * np.sum(tau**2)
        r_yaw = -0.05 * yaw_rate**2 - 0.5 * d.qvel[1] ** 2
        reward = r_vel + r_up + r_smooth + r_torque + r_yaw + 0.2
        self.prev_action = action

        terminated = bool(fallen(d))
        if terminated:
            reward -= 5.0
        truncated = self.t >= self.episode_steps
        info = {"terrain": self.key, "progress": float(d.qpos[0] - self.start_x), "x": float(d.qpos[0])}
        return self._obs(), float(reward), terminated, truncated, info

    def render(self):
        if self._renderer is None or self._renderer_model is not self.m:
            self._renderer = mujoco.Renderer(self.m, 360, 480)
            self._renderer_model = self.m
            self._cam = mujoco.MjvCamera()
            self._cam.distance, self._cam.azimuth, self._cam.elevation = 0.6, 105, -10
        self._cam.lookat[:] = [self.d.qpos[0], self.d.qpos[1], self.d.qpos[2] + 0.01]
        self._renderer.update_scene(self.d, camera=self._cam)
        return self._renderer.render()


Mini17Env = MiniEnv  # compatibilidad
