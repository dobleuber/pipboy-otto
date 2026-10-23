"""Imágenes del sistema de montaje (en un servidor sin pantalla: MUJOCO_GL=osmesa python render.py).

Arma con MuJoCo el brazo SO-101 real sobre las piezas exportadas (stl/), en la mesa y en el morral.
"""

import os
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sim"))
import scene  # noqa: E402

# Medidas que coinciden con params.scad (mm)
ARM_BASE = np.array([-100, -260, 0])
BAR_Y, BASE_Z0, BASE_H = 39, -2.4, 16
SHOULDER_H = 1450  # mm, altura de los hombros (igual que sim/backpack.py)
OUT = HERE.parent / "media"


def add_stl(spec, body, name, pos_mm=(0, 0, 0), rgba=(0.8, 0.8, 0.8, 1), quat=(1, 0, 0, 0)):
    mesh = spec.add_mesh()
    mesh.name, mesh.file, mesh.scale = f"m_{name}_{len(spec.meshes)}", str(HERE / "stl" / f"{name}.stl"), [1e-3] * 3
    g = body.add_geom()
    g.type, g.meshname = mujoco.mjtGeom.mjGEOM_MESH, mesh.name
    g.pos, g.rgba, g.quat = list(np.asarray(pos_mm) / 1000), list(rgba), list(quat)
    g.contype = g.conaffinity = 0
    return g


def mounted_cradle(spec, body, base_mm):
    add_stl(spec, body, "bandeja", base_mm, (0.85, 0.85, 0.88, 1))
    for s in (-1, 1):
        add_stl(spec, body, "barra", np.add(base_mm, [0, s * BAR_Y, BASE_Z0 + BASE_H]), (0.3, 0.3, 0.32, 1))


def arm_spec(base_m=None):
    spec = mujoco.MjSpec.from_file(str(scene.ensure_model())) if base_m is not None else mujoco.MjSpec()
    if base_m is not None:
        spec.body("base").pos = list(base_m)
    sky = spec.add_texture()
    sky.name, sky.type, sky.builtin = "sky", mujoco.mjtTexture.mjTEXTURE_SKYBOX, mujoco.mjtBuiltin.mjBUILTIN_GRADIENT
    sky.rgb1, sky.rgb2, sky.width, sky.height = [0.95, 0.95, 0.97], [0.75, 0.78, 0.82], 256, 1536
    spec.visual.global_.offwidth, spec.visual.global_.offheight = 1600, 1200
    spec.visual.headlight.ambient = [0.4, 0.4, 0.4]
    w = spec.worldbody
    li = w.add_light()
    li.pos, li.dir, li.type = [0.5, -1, 3], [-0.1, 0.3, -1], mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    return spec, w


def render(spec, views, q, path, title):
    m = spec.compile()
    d = mujoco.MjData(m)
    if q is not None:
        d.qpos[:5] = q
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 600, 600)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    tiles = []
    for (lookat, dist, az, el, label) in views:
        cam = mujoco.MjvCamera()
        cam.lookat[:], cam.distance, cam.azimuth, cam.elevation = lookat, dist, az, el
        r.update_scene(d, camera=cam)
        im = Image.fromarray(r.render())
        ImageDraw.Draw(im).text((12, 10), label, fill=(20, 20, 20), font=font)
        tiles.append(np.array(im))
    r.close()
    img = Image.fromarray(np.concatenate(tiles, 1))
    ImageDraw.Draw(img).text((12, 570), title, fill=(20, 20, 20), font=font)
    img.save(path)
    print("Imagen:", path)


def table():
    spec, w = arm_spec([0, 0, 0])
    # Mesa: la cara de arriba de la base de mesa apoya en z = 0 del mundo
    rail_z = BASE_Z0 - 4 - 9  # cara de abajo del riel respecto de la base del brazo (FLOOR=4, RAIL_H=9)
    mount_top = -(-rail_z) / 1000
    off = np.array([0, 0, 0])
    rx = np.array([-22.4 + 87 / 2 - 35 - 5, 0, rail_z])  # receptor centrado bajo la bandeja
    g = w.add_geom()
    g.type, g.size, g.pos, g.rgba = mujoco.mjtGeom.mjGEOM_BOX, [0.35, 0.3, 0.012], [0.12, 0, (rail_z - 8 - 8 - 12) / 1000], [0.75, 0.6, 0.45, 1]
    add_stl(spec, w, "base_mesa", rx + off, (0.6, 0.7, 0.85, 1))
    add_stl(spec, w, "receptor", rx, (0.85, 0.85, 0.88, 1))
    add_stl(spec, w, "mordaza", rx, (0.3, 0.3, 0.32, 1))
    mounted_cradle(spec, w, [0, 0, 0])
    views = [((0.05, 0, 0.03), 0.55, 135, -25, "En la mesa"), ((0.05, 0, 0.0), 0.35, 90, -8, "De costado")]
    render(spec, views, [0, -1.0, 1.0, 0.6, -1.57], OUT / "soporte_mesa.png",
           "Bandeja con riel + receptor con perilla + base para 2 prensas")


def backpack():
    shoulder = np.array([0, 0, SHOULDER_H])
    spec, w = arm_spec((ARM_BASE + shoulder) / 1000)
    # Persona simple (para escala) y morral transparente
    def box(pos, size, rgba, gtype=mujoco.mjtGeom.mjGEOM_BOX):
        g = w.add_geom()
        g.type, g.size, g.pos, g.rgba = gtype, size, list(np.asarray(pos) / 1000), rgba
        g.contype = g.conaffinity = 0
    box(shoulder + [0, 0, -270], [0.11, 0.19, 0.28], [0.2, 0.45, 0.35, 1])
    box(shoulder + [20, 0, 200], [0.1, 0, 0], [0.35, 0.37, 0.42, 1], mujoco.mjtGeom.mjGEOM_SPHERE)
    box(shoulder + [10, 0, 70], [0.05, 0.04, 0], [0.35, 0.37, 0.42, 1], mujoco.mjtGeom.mjGEOM_CAPSULE)
    box(shoulder + [-200, 0, -200], [0.085, 0.165, 0.23], [0.75, 0.35, 0.15, 0.25])
    for name, rgba in [("pie_mastil", (0.4, 0.42, 0.48, 1)), ("cabeza_fija", (0.4, 0.42, 0.48, 1)),
                       ("cabeza_movil", (0.6, 0.7, 0.85, 1))]:
        add_stl(spec, w, name, shoulder, rgba)
    # Tubo de aluminio (entre los mismos puntos que en params.scad)
    a, b = np.array([-154, -100, -60]) + shoulder, np.array([-154, -225, -45]) + shoulder
    g = w.add_geom()
    g.type, g.size, g.rgba = mujoco.mjtGeom.mjGEOM_BOX, [0.01, 0.01, 0], [0.75, 0.76, 0.78, 1]
    g.fromto = list(np.r_[a, b] / 1000)
    # Placa de la espalda y caja de electrónica
    box(shoulder + [-136.5, 0, -40 - 190], [0.0015, 0.125, 0.19], [0.92, 0.92, 0.92, 0.9])
    box(shoulder + [-138 - 25, 0, -330], [0.025, 0.0725, 0.049], [0.3, 0.4, 0.25, 1])
    mounted_cradle(spec, w, ARM_BASE + shoulder)
    c = (shoulder + [-120, -120, -150]) / 1000
    views = [(c, 1.45, 30, -15, "En el morral (hombro derecho)"), (c, 1.45, 300, -15, "Desde atrás")]
    render(spec, views, [0.2, -0.9, 0.9, -0.7, -1.57], OUT / "soporte_morral.png",
           "Placa (bolsillo de la laptop) + pie + tubo 20x20 + cabeza con bisagra + receptor")


HINGE = np.array([-148.9, -260, -31.4])  # eje de la bisagra (params.scad)


def head_detail():
    """La cabeza sola: cerrada y doblada hacia atrás (como cuando el brazo se engancha)."""
    tiles = []
    for fold in (0, 60):
        spec, w = arm_spec()
        li = w.add_light()
        li.pos, li.dir, li.type = [0.5, -1, 3], [-0.1, 0.3, -1], mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
        spec.visual.global_.offwidth, spec.visual.global_.offheight = 1600, 1200
        for name, rgba in [("pie_mastil", (0.4, 0.42, 0.48, 1)), ("cabeza_fija", (0.4, 0.42, 0.48, 1))]:
            add_stl(spec, w, name, (0, 0, 0), rgba)
        # Parte móvil (y lo que lleva encima) girada alrededor de la bisagra
        th = -np.radians(fold)
        q = [np.cos(th / 2), 0, np.sin(th / 2), 0]
        Ry = np.array([[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]])
        def rot(p):
            return HINGE + Ry @ (np.asarray(p, float) - HINGE)
        add_stl(spec, w, "cabeza_movil", rot([0, 0, 0]), (0.6, 0.7, 0.85, 1), q)
        add_stl(spec, w, "bandeja", rot(ARM_BASE), (0.85, 0.85, 0.88, 1), q)
        for sgn in (-1, 1):
            add_stl(spec, w, "barra", rot(ARM_BASE + [0, sgn * BAR_Y, BASE_Z0 + BASE_H]), (0.3, 0.3, 0.32, 1), q)
        a, b = np.array([-154, -100, -60]), np.array([-154, -225, -45])
        g = w.add_geom()
        g.type, g.size, g.rgba = mujoco.mjtGeom.mjGEOM_BOX, [0.01, 0.01, 0], [0.75, 0.76, 0.78, 1]
        g.fromto = list(np.r_[a, b] / 1000)
        m = spec.compile()
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        r = mujoco.Renderer(m, 600, 600)
        cam = mujoco.MjvCamera()
        cam.lookat[:], cam.distance, cam.azimuth, cam.elevation = np.array([-120, -220, -20]) / 1000, 0.42, 250, -20
        r.update_scene(d, camera=cam)
        im = Image.fromarray(r.render())
        r.close()  # con dos visores abiertos a la vez, osmesa devuelve basura
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        ImageDraw.Draw(im).text((12, 10), "Cerrada (imanes)" if fold == 0 else "Doblada 60° hacia atrás",
                                fill=(20, 20, 20), font=font)
        tiles.append(np.array(im))
    Image.fromarray(np.concatenate(tiles, 1)).save(OUT / "soporte_bisagra.png")
    print("Imagen:", OUT / "soporte_bisagra.png")


if __name__ == "__main__":
    os.environ.setdefault("MUJOCO_GL", "egl")
    table()
    backpack()
    head_detail()
