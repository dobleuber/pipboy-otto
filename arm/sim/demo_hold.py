"""Demo 2: el brazo agarra un objeto, se lo muestra a la persona, lo sostiene y lo devuelve.

Uso:
  python demo_hold.py                          # cubo de 30 g, imprime resultados
  python demo_hold.py --mass 0.2               # el mismo cubo pesando 200 g
  python demo_hold.py --video hold.mp4         # graba video
  python demo_hold.py --volts 7.4V             # servos de 7.4 V (menos torque)

La secuencia es programada (cinemática inversa); la posición del objeto se toma de la
simulación. En el robot real vendría de la cámara (o de aprendizaje por imitación).
"""

import argparse

import mujoco
import numpy as np

import scene
from control import CONTROL_HZ, REST, Arm, reach_velocity

OPEN, CLOSED = 1.2, -0.17  # pinza (rad); "cerrada" aprieta contra el objeto
DOWN = np.array([0.0, 0.0, -1.0])
# Al volver en alto la pinza va inclinada ~20°: vertical, la muñeca llega a su tope
TILTED = np.array([0.35, 0.0, -1.0]) / np.linalg.norm([0.35, 0.0, -1.0])
FORWARD = np.array([1.0, 0.0, 0.0])


def plan(obj0):
    """Pasos: (nombre, objetivo de la pinza, dirección de la pinza, pinza, segundos)."""
    # La mandíbula fija queda 2 cm al costado (+y) del punto de agarre: se corre 6 mm para que
    # baje por fuera del cubo; al cerrar, la móvil lo empuja contra ella.
    side = np.array([0, 0.006, 0])
    above = obj0 + side + [0, 0, 0.07]
    grasp = obj0 + side + [0, 0, -0.005]
    show = np.array([0.30, 0.0, 0.24])
    return [
        ("acercarse", above, DOWN, OPEN, 2.0),
        ("bajar", grasp, DOWN, OPEN, 1.5),
        ("agarrar", grasp, DOWN, CLOSED, 1.0),
        ("levantar", above, DOWN, CLOSED, 1.5),
        ("mostrar", show, FORWARD, CLOSED, 2.0),
        ("sostener", show, FORWARD, CLOSED, 4.0),
        ("volver", above, TILTED, CLOSED, 2.0),
        ("dejar", grasp + [0, 0, 0.012], DOWN, CLOSED, 1.5),
        ("soltar", grasp + [0, 0, 0.012], DOWN, OPEN, 0.8),
        ("retirarse", above, DOWN, OPEN, 1.2),
    ]


def run(obj="cube", mass=None, volts="12V", video=None):
    m = scene.build(volts)
    body = m.body(obj).id
    if mass:
        m.body_inertia[body] *= mass / m.body_mass[body]  # misma forma, más pesado
        m.body_mass[body] = mass
    d = mujoco.MjData(m)
    mujoco.mj_setConst(m, d)  # recalcula lo que depende de la masa (si no, el contacto explota)
    arm = Arm(m, d)
    arm.set_pose(REST)
    arm.grip_cmd = OPEN
    d.mocap_pos[0] = [0.95, 0.0, 0.0]
    mujoco.mj_forward(m, d)
    rec = Recorder(m) if video else None
    obj0 = d.xpos[body].copy()

    log = {}
    for name, target, approach, grip, seconds in plan(obj0):
        arm.grip_cmd = grip
        tq, errs = [], []
        for _ in range(int(seconds * CONTROL_HZ)):
            dq, err = reach_velocity(arm, target, approach)
            arm.move(dq)
            arm.step()
            tq.append(np.abs(d.actuator_force[arm.act]))
            errs.append(err)
            if rec:
                rec.frame(d, name)
        log[name] = dict(torque=np.array(tq), err=errs[-1], obj_z=float(d.xpos[body][2]),
                         obj_to_grip=float(np.linalg.norm(d.xpos[body] - arm.site_pose()[0])))
    if rec:
        rec.save(video)

    held = log["sostener"]
    return {
        "mass_g": 1000 * float(m.body_mass[body]),
        # Sostenido = el objeto sigue en la pinza (a menos de 3 cm) y arriba de la mesa
        "held": held["obj_to_grip"] < 0.03 and held["obj_z"] > 0.1,
        "hold_torque": held["torque"][-25:].mean(0),  # promedio del último segundo
        "max_torque": max(float(v["torque"].max()) for v in log.values()),
        "placed_back": log["retirarse"]["obj_z"] < 0.05,
        "reach_err_mm": {k: 1000 * v["err"] for k, v in log.items()},
    }


class Recorder:
    def __init__(self, m):
        from PIL import ImageFont

        self.r = mujoco.Renderer(m, 480, 640)
        self.cam_r = mujoco.Renderer(m, 168, 224)
        self.frames = []
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)

    def frame(self, d, step):
        from PIL import Image, ImageDraw

        self.r.update_scene(d, camera="side")
        big = Image.fromarray(self.r.render())
        self.cam_r.update_scene(d, camera="wrist_cam")
        big.paste(Image.fromarray(self.cam_r.render()), (8, 8))
        dr = ImageDraw.Draw(big)
        dr.rectangle([8, 8, 232, 176], outline=(255, 255, 255), width=2)
        dr.text((12, 180), "cámara del brazo", fill=(255, 255, 255), font=self.font)
        dr.text((470, 10), step, fill=(255, 230, 90), font=self.font)
        self.frames.append(np.array(big))

    def save(self, path):
        import imageio.v2 as iio

        iio.mimsave(path, self.frames, fps=CONTROL_HZ, macro_block_size=1)
        print("Video guardado en", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--object", default="cube", choices=["cube", "ball", "can"])
    ap.add_argument("--mass", type=float, help="kg (por defecto el del objeto)")
    ap.add_argument("--volts", default="12V", choices=list(scene.STALL_TORQUE))
    ap.add_argument("--video")
    args = ap.parse_args()
    out = run(args.object, args.mass, args.volts, args.video)
    names = ["base", "hombro", "codo", "muñeca", "giro muñeca"]
    print(f"Objeto: {args.object}, {out['mass_g']:.0f} g, servos {args.volts}")
    print("Lo sostuvo:", "sí" if out["held"] else "NO", "| Lo devolvió a la mesa:", "sí" if out["placed_back"] else "no")
    print("Torque al sostener (N·m):", ", ".join(f"{n} {t:.2f}" for n, t in zip(names, out["hold_torque"])))
    print(f"Torque máximo: {out['max_torque']:.2f} N·m (límite {scene.STALL_TORQUE[args.volts]} N·m)")


if __name__ == "__main__":
    main()
