"""Compara la caminata programada contra la política entrenada en cada terreno.

Uso:
  python evaluate.py --policy runs/mix/policy.zip                  # tabla de resultados
  python evaluate.py --policy runs/mix/policy.zip --video out_dir  # + videos lado a lado
  python evaluate.py --policy mini16_policy.onnx                   # también acepta ONNX

Éxito = no se cae y avanza al menos 30 cm (en escalones: sube al menos el primero).
Cada terreno se prueba con varias semillas, con fricción/peso/servos aleatorios y empujones.
"""

import argparse
from pathlib import Path

import numpy as np

from env import TERRAINS, MiniEnv

SUCCESS_PROGRESS = 0.3


ROBOT = None  # se fija con --robot


def n_leg():
    import robots

    return robots.get(ROBOT).n_leg


def load_policy(path):
    if path is None:
        return lambda obs: np.zeros(n_leg(), np.float32)  # caminata programada sola
    if str(path).endswith(".onnx"):
        import onnxruntime as ort

        sess = ort.InferenceSession(str(path))
        name = sess.get_inputs()[0].name
        return lambda obs: sess.run(None, {name: obs[None].astype(np.float32)})[0][0]
    from stable_baselines3 import PPO

    model = PPO.load(path, device="cpu")
    return lambda obs: model.predict(obs, deterministic=True)[0]


def run_episode(policy, terrain, seed, frames=None, seconds=10.0):
    env = MiniEnv(terrain=[terrain], robot=ROBOT, episode_seconds=seconds, seed=seed)
    obs, _ = env.reset(seed=seed)
    fell = False
    while True:
        obs, _, term, trunc, info = env.step(policy(obs))
        if frames is not None and env.t % 2 == 0:  # 25 fps
            frames.append(env.render())
        if term:
            fell = True
            if frames is None:
                break
            # sigue grabando un poco para mostrar la caída
            for _ in range(25):
                env.step(np.zeros(env.n_leg))
                frames.append(env.render())
            break
        if trunc:
            break
    return {"progress": info["progress"], "fell": fell, "ok": (not fell) and info["progress"] >= SUCCESS_PROGRESS}


def evaluate(policy, terrains, seeds):
    rows = {}
    for t in terrains:
        res = [run_episode(policy, t, s) for s in seeds]
        rows[t] = (np.mean([r["ok"] for r in res]), np.mean([r["progress"] for r in res]))
    return rows


def label(t):
    kind, v = t
    return {"flat": "Plano", "ramp": f"Rampa {v}°", "step": f"Escalones {v * 100:g} cm"}[kind]


def side_by_side_video(policies, names, terrain, path, seed=0):
    import imageio.v2 as iio
    from PIL import Image, ImageDraw, ImageFont

    font = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)  # noqa: E731
    cols, outs = [], []
    for pol in policies:
        fr = []
        outs.append(run_episode(pol, terrain, seed, frames=fr))
        cols.append(fr)
    n = max(len(c) for c in cols)
    W, H = 480, 360
    video = []
    for i in range(n):
        im = Image.new("RGB", (W * len(cols), H + 96), (15, 15, 18))
        dr = ImageDraw.Draw(im)
        dr.text((12, 8), label(terrain), fill=(255, 255, 255), font=font(30))
        for j, c in enumerate(cols):
            im.paste(Image.fromarray(c[min(i, len(c) - 1)]), (j * W, 96))
            dr.text((j * W + 10, 52), names[j], fill=(230, 230, 230), font=font(22))
            if i >= len(c) - 1 or i > n - 40:
                o = outs[j]
                txt, col = (("se cayó", (230, 80, 80)) if o["fell"] else
                            (("lo logró", (90, 200, 90)) if o["ok"] else ("trabado", (240, 170, 60))))
                dr.text((j * W + 330, 52), txt, fill=col, font=font(22))
        video.append(np.array(im))
    iio.mimsave(path, video, fps=25, macro_block_size=1)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", help="policy.zip o .onnx (sin esto: solo la caminata programada)")
    ap.add_argument("--robot", default=None, help="mini16 (por defecto) o mini13")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--video", help="carpeta para guardar videos comparativos")
    args = ap.parse_args()
    global ROBOT
    ROBOT = args.robot

    terrains = TERRAINS["mix"]
    seeds = list(range(100, 100 + args.seeds))
    base = evaluate(load_policy(None), terrains, seeds)
    pol = load_policy(args.policy) if args.policy else None
    trained = evaluate(pol, terrains, seeds) if pol else None

    print(f"{'Terreno':<18}{'Programada':>22}{'Con IA':>22}")
    for t in terrains:
        b = f"{base[t][0] * 100:3.0f}% ({base[t][1] * 100:4.0f} cm)"
        r = f"{trained[t][0] * 100:3.0f}% ({trained[t][1] * 100:4.0f} cm)" if trained else "-"
        print(f"{label(t):<18}{b:>22}{r:>22}")

    if args.video and pol:
        out = Path(args.video)
        out.mkdir(parents=True, exist_ok=True)
        for t in [("ramp", 15), ("ramp", 20), ("step", 0.01), ("step", 0.015)]:
            name = f"{t[0]}_{t[1]}".replace(".", "_")
            side_by_side_video([load_policy(None), pol], ["Caminata programada", "Con IA"], t,
                               str(out / f"{name}.mp4"))
            print("video:", out / f"{name}.mp4")


if __name__ == "__main__":
    main()
