"""Demo 1: el brazo busca a una persona con su cámara, la saluda y la sigue con la mirada.

Uso:
  python demo_track.py                       # simula e imprime resultados
  python demo_track.py --video track.mp4     # además graba video (vista externa + cámara)
  MUJOCO_GL=osmesa python demo_track.py ...  # en un servidor sin pantalla

El brazo solo usa la imagen de su cámara de muñeca (detector de piel) y sus propios ángulos.
La posición real de la persona se usa solo para medir qué tan bien la sigue.
"""

import argparse

import mujoco
import numpy as np

import scene
from control import CONTROL_HZ, REST, Arm, detect_face, look_velocity

DET_W, DET_H = 160, 120  # resolución para detectar (el robot real usaría algo parecido)


def person_path(t):
    """Recorrido de la persona: (x, y, z) del cuerpo."""
    if t < 4:  # sentada al frente
        return 0.95, 0.0, 0.0
    if t < 10:  # se mueve de lado a lado
        return 0.95, 0.28 * np.sin((t - 4) * 2 * np.pi / 6), 0.0
    if t < 13:  # se acerca y se levanta un poco
        k = (t - 10) / 3
        return 0.95 - 0.2 * np.sin(np.pi * k), 0.0, 0.12 * np.sin(np.pi * k)
    if t < 14:  # se va caminando hacia un lado...
        return 0.95 + 0.6 * (t - 13), -0.6 * (t - 13), 0.0
    if t < 17:  # ...y sale de la habitación
        return 0.95, 0.0, -5.0
    if t < 20:  # vuelve por el otro lado
        return 0.95, 0.7 - 0.7 * (t - 17) / 3, 0.0
    return 0.95, 0.0, 0.0


def run(seconds=23.0, video=None, volts="12V"):
    m = scene.build(volts)
    d = mujoco.MjData(m)
    arm = Arm(m, d)
    arm.set_pose(REST)
    arm.grip_cmd = 0.0
    det = mujoco.Renderer(m, DET_H, DET_W)
    face = m.geom("face").id
    rec = Recorder(m) if video else None

    state, lost_for, t_seen, nod_until = "buscar", 0.0, None, -1.0
    stats = dict(frames=0, seen=0, err=[], torque=[], states=[])
    n = int(seconds * CONTROL_HZ)
    for k in range(n):
        t = k / CONTROL_HZ
        d.mocap_pos[0] = person_path(t)
        mujoco.mj_forward(m, d)

        det.update_scene(d, camera="wrist_cam")
        img = det.render()
        hit = detect_face(img)
        if hit:
            lost_for = 0.0
            if state == "buscar":
                state, nod_until = "saludar", t + 1.2
        else:
            lost_for += 1 / CONTROL_HZ
            if lost_for > 0.8:
                state = "buscar"

        if state == "buscar":
            # Barrido: gira la base de lado a lado con la mirada al frente
            target = REST.copy()
            target[0] = 1.2 * np.sin(2 * np.pi * t / 6)
            dq = 2.0 * (target - d.qpos[arm.qadr])
        else:
            dq = look_velocity(arm, *(hit[:2] if hit else (0.0, 0.0)))
            if state == "saludar":
                # Asiente con la "cabeza" (muñeca) al encontrar a alguien
                dq[3] += 1.5 * np.cos(2 * np.pi * 1.6 * t)
                if t > nod_until:
                    state = "seguir"
        arm.move(dq)
        arm.step()

        # Métricas: ángulo entre la mirada y la cara real
        cpos, Rc = arm.cam_frame()
        to_face = d.geom_xpos[face] - cpos
        ang = np.degrees(np.arccos(np.clip(-Rc[:, 2] @ to_face / np.linalg.norm(to_face), -1, 1)))
        stats["frames"] += 1
        stats["seen"] += bool(hit)
        if state == "seguir":
            stats["err"].append(ang)
        stats["torque"].append(np.abs(d.actuator_force[arm.act]))
        stats["states"].append(state)
        if rec:
            rec.frame(d, img, state, hit, t)

    if rec:
        rec.save(video)
    err = np.array(stats["err"]) if stats["err"] else np.array([np.nan])
    return {
        "visible_pct": 100 * stats["seen"] / stats["frames"],
        "track_err_median_deg": float(np.median(err)),
        "track_err_p90_deg": float(np.percentile(err, 90)),
        "max_torque": float(np.max(stats["torque"])),
        # Torque al seguir (percentil 99): lo que el servo hace la mayor parte del tiempo
        "p99_torque_follow": float(np.percentile(
            [tq.max() for tq, s in zip(stats["torque"], stats["states"]) if s == "seguir"], 99)),
        "torque": np.array(stats["torque"]),
        "states": stats["states"],
    }


class Recorder:
    """Video: vista externa grande + lo que ve la cámara del brazo en una esquina."""

    LABEL = {"buscar": "buscando...", "saludar": "¡hola!", "seguir": "siguiendo"}

    def __init__(self, m):
        from PIL import ImageFont

        self.r = mujoco.Renderer(m, 480, 640)
        self.frames = []
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)

    def frame(self, d, cam_img, state, hit, t):
        from PIL import Image, ImageDraw

        self.r.update_scene(d, camera="side")
        big = Image.fromarray(self.r.render())
        small = Image.fromarray(cam_img).resize((224, 168))
        dr = ImageDraw.Draw(small)
        if hit:
            u, v, size = hit
            cx, cy = (u + 1) / 2 * 224, (v + 1) / 2 * 168
            rad = max(8, 120 * np.sqrt(size))
            dr.rectangle([cx - rad, cy - rad, cx + rad, cy + rad], outline=(60, 230, 90), width=3)
        big.paste(small, (8, 8))
        dr = ImageDraw.Draw(big)
        dr.rectangle([8, 8, 232, 176], outline=(255, 255, 255), width=2)
        dr.text((12, 180), "cámara del brazo", fill=(255, 255, 255), font=self.font)
        dr.text((470, 10), self.LABEL[state], fill=(255, 230, 90), font=self.font)
        dr.text((470, 36), f"{t:4.1f} s", fill=(230, 230, 230), font=self.font)
        self.frames.append(np.array(big))

    def save(self, path):
        import imageio.v2 as iio

        iio.mimsave(path, self.frames, fps=CONTROL_HZ, macro_block_size=1)
        print("Video guardado en", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--seconds", type=float, default=23.0)
    ap.add_argument("--volts", default="12V", choices=list(scene.STALL_TORQUE))
    args = ap.parse_args()
    out = run(args.seconds, args.video, args.volts)
    states = out.pop("states")
    out.pop("torque")
    print(f"Cara visible: {out['visible_pct']:.0f} % del tiempo (la persona sale de la vista a propósito)")
    print(f"Error de mirada al seguir: mediana {out['track_err_median_deg']:.1f}°, p90 {out['track_err_p90_deg']:.1f}°")
    print(f"Torque: máximo {out['max_torque']:.2f} N·m, al seguir (p99) {out['p99_torque_follow']:.2f} N·m "
          f"(límite {scene.STALL_TORQUE[args.volts]} N·m)")
    print("Saludos:", sum(1 for i, s in enumerate(states) if s == "saludar" and (i == 0 or states[i - 1] != "saludar")))


if __name__ == "__main__":
    main()
