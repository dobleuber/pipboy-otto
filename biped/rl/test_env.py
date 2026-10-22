"""Pruebas del entorno de entrenamiento. Correr con: python -m pytest -q"""

import numpy as np
import pytest

from env import N_RAYS, Mini17Env


@pytest.fixture(scope="module")
def env():
    return Mini17Env(terrain="mix", seed=0)


def test_spaces_and_observation(env):
    obs, info = env.reset(seed=1, options={"terrain": ("flat", 0)})
    assert env.observation_space.shape == obs.shape
    assert env.action_space.shape == (12,)
    assert np.all(np.isfinite(obs))


def test_zero_action_walks_on_flat(env):
    """Con acción cero es la caminata programada: debe avanzar sin caerse."""
    env.reset(seed=2, options={"terrain": ("flat", 0)})
    for _ in range(250):
        obs, r, term, trunc, info = env.step(np.zeros(12))
        assert not term
    assert info["progress"] > 0.15


def test_distance_sensor_sees_step(env):
    obs, _ = env.reset(seed=3, options={"terrain": ("step", 0.02)})
    rays = obs[-N_RAYS:]
    # Los primeros rayos ven el piso; los últimos, el escalón (más cerca del torso).
    assert rays[0] > rays[-1] + 0.2


def test_servo_speed_limit(env):
    env.reset(seed=4, options={"terrain": ("flat", 0)})
    prev = env.d.ctrl[:12].copy()
    env.step(np.ones(12))
    assert np.all(np.abs(env.d.ctrl[:12] - prev) <= 4.7 / 50 + 1e-9)
