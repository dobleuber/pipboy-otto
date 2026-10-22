"""Exporta la política entrenada a ONNX para correrla en la Raspberry Pi.

Uso:
  python export_onnx.py runs/mix/policy.zip mini17_policy.onnx

El archivo ONNX recibe la observación (ver env.py) y devuelve las 12 correcciones
de los motores de pierna en [-1, 1]. En el robot: objetivo = caminata programada
+ 0.3 rad * corrección, a 50 Hz.
"""

import sys

import numpy as np
import torch
from stable_baselines3 import PPO


class Actor(torch.nn.Module):
    def __init__(self, policy):
        super().__init__()
        self.features = policy.mlp_extractor.policy_net
        self.head = policy.action_net

    def forward(self, obs):
        return torch.clamp(self.head(self.features(obs)), -1.0, 1.0)


def main(src, dst):
    model = PPO.load(src, device="cpu")
    actor = Actor(model.policy).eval()
    n_obs = model.observation_space.shape[0]
    dummy = torch.zeros(1, n_obs)
    torch.onnx.export(actor, dummy, dst, input_names=["obs"], output_names=["action"],
                      dynamic_axes={"obs": {0: "batch"}, "action": {0: "batch"}}, opset_version=17,
                      dynamo=False)
    # Verificación: ONNX == PyTorch
    import onnxruntime as ort

    sess = ort.InferenceSession(dst)
    x = np.random.default_rng(0).normal(size=(8, n_obs)).astype(np.float32)
    a_onnx = sess.run(None, {"obs": x})[0]
    a_sb3 = np.stack([model.predict(xi, deterministic=True)[0] for xi in x])
    err = float(np.abs(a_onnx - np.clip(a_sb3, -1, 1)).max())
    print(f"Exportado a {dst} (diferencia máx. con PyTorch: {err:.2e})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
