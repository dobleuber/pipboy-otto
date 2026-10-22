"""Pruebas del entorno de entrenamiento. Correr con: python -m pytest -q"""

import numpy as np
import pytest

from env import N_RAYS, MiniEnv


@pytest.fixture(scope="module", params=["mini13", "mini16"])
def env(request):
    return MiniEnv(terrain="mix", robot=request.param, seed=0)


def test_spaces_and_observation(env):
    obs, info = env.reset(seed=1, options={"terrain": ("flat", 0)})
    assert env.observation_space.shape == obs.shape
    assert env.action_space.shape == (env.n_leg,)
    assert np.all(np.isfinite(obs))


def test_zero_action_stands_on_flat(env):
    """Con acción cero es la caminata programada: con fricción, peso y servos aleatorios no debe
    caerse en 5 s. (No se exige avance: con las variaciones, la caminata programada de Mini16
    real casi no avanza; mejorar eso es el trabajo de la IA.)"""
    env.reset(seed=2, options={"terrain": ("flat", 0)})
    for _ in range(250):
        obs, r, term, trunc, info = env.step(np.zeros(env.n_leg))
        assert not term


def test_distance_sensor_sees_step(env):
    obs, _ = env.reset(seed=3, options={"terrain": ("step", 0.02)})
    rays = obs[-N_RAYS:]
    # Los primeros rayos ven el piso; los últimos, el escalón (más cerca del torso).
    assert rays[0] > rays[-1] + 0.2


def test_servo_speed_limit(env):
    env.reset(seed=4, options={"terrain": ("flat", 0)})
    n = env.n_leg
    prev = env.d.ctrl[:n].copy()
    env.step(np.ones(n))
    assert np.all(np.abs(env.d.ctrl[:n] - prev) <= 4.7 / 50 + 1e-9)
