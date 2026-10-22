"""Demo de Mini15 caminando.

Uso:
  python run_demo.py                      # simula 12 s e imprime resultados
  python run_demo.py --video mini15.mp4   # además graba un video (sin pantalla)
  python run_demo.py --viewer             # abre el visor interactivo de MuJoCo
  python run_demo.py --turn 0.15          # gira a la izquierda (negativo = derecha)
"""

import argparse
import os

from gait import GaitParams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--freq", type=float, default=GaitParams.freq, help="ciclos de paso por segundo")
    ap.add_argument("--step", type=float, default=GaitParams.step_len, help="largo de medio paso (m)")
    ap.add_argument("--lift", type=float, default=GaitParams.lift, help="altura del pie (m)")
    ap.add_argument("--turn", type=float, default=0.0, help="giro (+ izquierda, - derecha), ej. 0.15")
    ap.add_argument("--video", help="ruta .mp4 o .gif para grabar")
    ap.add_argument("--viewer", action="store_true", help="visor interactivo")
    args = ap.parse_args()

    params = GaitParams(freq=args.freq, step_len=args.step, lift=args.lift, turn=args.turn)

    if args.viewer:
        run_viewer(params)
        return

    on_frame, finish = (None, None)
    if args.video:
        on_frame, finish = make_recorder(args.video)

    from common import simulate

    out = simulate(params, args.seconds, on_frame)
    if finish:
        finish()

    print(f"Avanzó {out['x'] * 100:.0f} cm (desvío lateral {out['y'] * 100:.0f} cm) en {out['time']:.0f} s")
    print(f"Inclinación máxima del torso: {out['max_tilt_deg']:.1f}°, giro total: {out['yaw_deg']:.0f}°")
    print(f"Torque de pierna (p99): {out['p99_leg_torque']:.2f} N·m de 1.9 N·m")
    print("Se cayó a los %.1f s" % out["fell_at"] if out["fell_at"] else "No se cayó")


def make_recorder(path):
    os.environ.setdefault("MUJOCO_GL", "egl")
    import imageio.v2 as imageio
    import mujoco

    frames = []
    state = {}

    def on_frame(model, data):
        if "r" not in state:
            state["r"] = mujoco.Renderer(model, 480, 640)
            cam = mujoco.MjvCamera()
            cam.distance, cam.azimuth, cam.elevation = 0.5, 150, -12
            state["cam"] = cam
        cam = state["cam"]
        cam.lookat[:] = [data.qpos[0], data.qpos[1], 0.12]
        state["r"].update_scene(data, camera=cam)
        frames.append(state["r"].render())

    def finish():
        if path.endswith(".gif"):
            imageio.mimsave(path, frames[::2], duration=1 / 15, loop=0)
        else:
            imageio.mimsave(path, frames, fps=30)
        print(f"Video guardado en {path}")

    return on_frame, finish


def run_viewer(params):
    import time

    import mujoco
    import mujoco.viewer

    from common import CONTROL_HZ, load, torso_pitch_roll
    from gait import targets

    model, data = load()
    every = int(round(1 / (CONTROL_HZ * model.opt.timestep)))
    with mujoco.viewer.launch_passive(model, data) as v:
        i = 0
        while v.is_running():
            start = time.time()
            if i % every == 0:
                pitch, roll = torso_pitch_roll(data)
            data.ctrl[:] = targets(data.time, params, pitch, roll)
            mujoco.mj_step(model, data)
            i += 1
            if i % 10 == 0:
                v.sync()
            time.sleep(max(0, model.opt.timestep - (time.time() - start)))


if __name__ == "__main__":
    main()
