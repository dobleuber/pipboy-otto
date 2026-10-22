"""Entrena a Mini13 / Mini17 con PPO (Stable-Baselines3) en terrenos variados.

Uso:
  python train.py --steps 5000000 --envs 4            # entrenamiento local en CPU (Mini13)
  python train.py --robot mini17 --out runs/mini17     # el de 17 motores
  python train.py --steps 200000 --envs 2 --out runs/prueba   # prueba rápida

Guarda en --out: modelo final (policy.zip), checkpoints y un log CSV con el progreso.
En una PC con más núcleos, subir --envs acelera casi en proporción.
"""

import argparse
import csv
import os
import time
from pathlib import Path

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from env import MiniEnv  # noqa: I001 (env añade sim/ al path)
import robots  # noqa: E402


def make_env(terrain, seed, robot):
    def _f():
        torch.set_num_threads(1)
        return MiniEnv(terrain=terrain, robot=robot, seed=seed)

    return _f


class ProgressLog(BaseCallback):
    """Escribe recompensa media y avance medio por terreno cada rollout."""

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.t0 = time.time()
        self.per_terrain = {}
        self.rows = 0

    def _on_step(self):
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            if done:
                k = f"{info['terrain'][0]}{info['terrain'][1]}"
                self.per_terrain.setdefault(k, []).append(info["progress"])
        return True

    def _on_rollout_end(self):
        ep = self.model.ep_info_buffer
        rew = float(np.mean([e["r"] for e in ep])) if ep else 0.0
        length = float(np.mean([e["l"] for e in ep])) if ep else 0.0
        row = {"steps": self.num_timesteps, "minutes": round((time.time() - self.t0) / 60, 1),
               "reward": round(rew, 1), "ep_len": round(length)}
        for k, v in sorted(self.per_terrain.items()):
            row[f"avance_{k}"] = round(float(np.mean(v[-20:])), 3)
        new = not os.path.exists(self.path)
        with open(self.path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()), extrasaction="ignore")
            if new or self.rows == 0:
                w.writeheader()
            w.writerow(row)
        self.rows += 1
        print(row, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=5_000_000)
    ap.add_argument("--envs", type=int, default=4)
    ap.add_argument("--terrain", default="mix", choices=["flat", "ramps", "steps", "mix"])
    ap.add_argument("--robot", default=None, help="mini17 (por defecto) o mini13")
    ap.add_argument("--out", default="runs/mix")
    ap.add_argument("--resume", help="policy.zip para continuar entrenando")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    env = VecMonitor(SubprocVecEnv([make_env(args.terrain, 1000 + i, args.robot) for i in range(args.envs)]))

    if args.resume:
        model = PPO.load(args.resume, env=env, device="cpu")
    else:
        model = PPO(
            "MlpPolicy",
            env,
            n_steps=2048,
            batch_size=2048,
            n_epochs=5,
            learning_rate=3e-4,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.0,
            max_grad_norm=0.5,
            # Política chica: corre fácil en una Raspberry Pi Zero 2W.
            policy_kwargs=dict(net_arch=dict(pi=[128, 128], vf=[128, 128]), log_std_init=robots.get(args.robot).rl_log_std,
                               activation_fn=torch.nn.ELU),
            device="cpu",
            seed=0,
            verbose=0,
        )
    callbacks = [ProgressLog(str(out / "progress.csv")),
                 CheckpointCallback(save_freq=max(1, 500_000 // args.envs), save_path=str(out / "checkpoints"))]
    model.learn(total_timesteps=args.steps, callback=callbacks, reset_num_timesteps=not args.resume)
    model.save(out / "policy.zip")
    print("Guardado en", out / "policy.zip")


if __name__ == "__main__":
    main()
