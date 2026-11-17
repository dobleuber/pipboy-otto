"""Diseño generativo de la cabeza fija del soporte del morral (prueba).

Marco de la pieza (mm, N): X = adelante del usuario, desde el eje de la bisagra; Y = hacia ABAJO,
desde la cara de apoyo de la placa móvil (Y < 0 es donde se mueve la parte móvil); Z = hacia la
izquierda del usuario, desde la cara exterior del lado derecho. Z = 0 es la cama de impresión.
El eje de la bisagra (pasador M8) y el tubo de aluminio corren a lo largo de Z.

Para la prueba el tubo es horizontal (en el diseño sube 15 mm en 125 mm, ~7°): así el tubo y el
pasador son paralelos y todos los agujeros importantes van a lo largo de Z. La pieza original de
comparación (baselines/cabeza_fija.stl) es la misma cabeza_fija con el tubo horizontal
(head_fixed_level.scad).

Cargas (de la simulación del morral, arm/sim/demo_walk.py), con 1.5 de margen:
  - caminar sosteniendo 500 g: el soporte recibe ~16 N y ~3.3 N·m -> 24 N hacia abajo, a 206 mm
    adelante de la base del brazo (3.3 / 16) y 100 mm arriba (centro de masa del brazo);
  - lo mismo con un empuje de costado de la mitad, a cada lado (el vaivén de la marcha);
  - la rama: la pinza empujada hacia atrás con 20 N (lo máximo antes de que cedan los imanes:
    7 N·m / 0.35 m), más el peso del brazo;
  - los imanes a punto de ceder: tiran de la cara de apoyo hacia arriba con ~100 N (7 N·m a ~70 mm
    de la bisagra) y el pasador empuja hacia abajo lo mismo.
"""
from genpart import Problem, RemoteLoad, box, zcyl

# Medidas (de arm/cad/params.scad y mounts.scad, pasadas a este marco)
LUG_Z = (14.4, 55.6)          # nudillo central (fijo) de la bisagra, r = 11
KR = 11.0
SUPPORT_X = (14.0, 105.0)     # apoyo bajo la placa móvil
SUPPORT_Z = (0.0, 70.0)
MAGNETS = [(55.0, 9.0), (85.0, 9.0), (55.0, 61.0), (85.0, 61.0)]   # (X, Z), huecos de 10.3 x 5.2 desde Y = 0
RX_BOLTS = [(40.0, 6.0), (40.0, 64.0), (95.0, 6.0), (95.0, 64.0)]  # rebajes para los tornillos del receptor
TUBE = (-5.1, 28.6)           # centro del tubo (X, Y)
SOCKET_Z = (62.0, 107.0)      # el tubo entra hasta Z = 70; el encastre va de 62 a 107
CROSS_Z = (74.0, 95.0)        # pasadores M5 a través del encastre (a lo largo de Y)

# Puntos de aplicación (marco de la pieza)
ARM_LOAD_POINT = (255.0, -131.0, 35.0)     # 206 mm adelante de la base del brazo, 100 mm arriba
BRANCH_POINT = (305.0, -351.0, 35.0)       # la pinza, a 1.77 m de altura


def cabeza_fija():
    lug = zcyl(0, 0, KR, LUG_Z[0], LUG_Z[1])
    skin = box(SUPPORT_X[0], SUPPORT_X[1], 0, 3, SUPPORT_Z[0], SUPPORT_Z[1])   # cara de apoyo plana
    # Las cargas del brazo entran por la bisagra y por la cara de apoyo; cada una partida en dos
    # mitades (en Z) para que puedan tomar giros
    mid = 35.0
    arm_patches = [zcyl(0, 0, KR, LUG_Z[0], mid), zcyl(0, 0, KR, mid, LUG_Z[1]),
                   box(SUPPORT_X[0], SUPPORT_X[1], 0, 3, SUPPORT_Z[0], mid),
                   box(SUPPORT_X[0], SUPPORT_X[1], 0, 3, mid, SUPPORT_Z[1])]
    bosses = [box(x - 8, x + 8, 0, 8, z - 8, z + 8) for x, z in MAGNETS]      # alrededor de los imanes
    tx, ty = TUBE
    socket = box(tx - 15, tx + 15, ty - 15, ty + 15, SOCKET_Z[0], SOCKET_Z[1])
    return Problem(
        name="cabeza_fija",
        # Lugar: hasta 1 cm más atrás que la original y 1.2 cm más abajo; adelante lo limita el hombro
        bounds=(-30, 105, -11, 55, 0, 107),
        keepout=[
            # Encima de la cara de apoyo se mueve la parte móvil (y se dobla hacia atrás): todo libre,
            # salvo el nudillo central (que entra en el hueco de la placa móvil, radio 12)
            box(-99, 99, -99, 0, -99, LUG_Z[0] - 0.2),
            box(-99, 99, -99, 0, LUG_Z[1] + 0.2, 99),
            box(8.5, 99, -99, 0, LUG_Z[0] - 1, LUG_Z[1] + 1),
            box(-99, -8.5, -99, 0, LUG_Z[0] - 1, LUG_Z[1] + 1),
            box(-99, 99, -99, -8.5, LUG_Z[0] - 1, LUG_Z[1] + 1),
            # Nudillos móviles a los lados del fijo (giran: cilindro completo de radio 12.5)
            zcyl(0, 0, 12.5, -99, LUG_Z[0] - 0.2),
            zcyl(0, 0, 12.5, LUG_Z[1] + 0.2, 99),
            # El tubo de aluminio (20 x 20 + holgura), desde Z = 70 hacia el pie
            box(tx - 10.4, tx + 10.4, ty - 10.4, ty + 10.4, SOCKET_Z[0], 99),
            # Cabezas y tuercas de los pasadores M5 del encastre (arriba y abajo) y la llave
            *[box(tx - 6, tx + 6, -99, ty - 15, z - 6, z + 6) for z in CROSS_Z],
            *[box(tx - 6, tx + 6, ty + 15, 99, z - 6, z + 6) for z in CROSS_Z],
            # Rebajes para las cabezas de los tornillos del receptor (en la placa móvil)
            *[box(x - 6, x + 6, -1, 4.5, z - 6, z + 6) for x, z in RX_BOLTS],
        ],
        preserve=[lug, skin, *bosses, socket],
        holes=[
            zcyl(0, 0, 4.2, -99, 99),                                                  # pasador M8
            *[box(x - 5.2, x + 5.2, -1, 5.2, z - 5.2, z + 5.2) for x, z in MAGNETS],   # imanes 10 x 5
            *[box(tx - 2.7, tx + 2.7, -99, 99, z - 2.7, z + 2.7) for z in CROSS_Z],    # pasadores M5
        ],
        support=[box(tx - 15, tx + 15, ty - 15, ty + 15, 75, 107)],   # el tubo la sostiene
        cases={
            "caminar con 500 g": [RemoteLoad(arm_patches, ARM_LOAD_POINT, (0, 24, 0))],
            "caminar, empuje a la izquierda": [RemoteLoad(arm_patches, ARM_LOAD_POINT, (0, 24, 12))],
            "caminar, empuje a la derecha": [RemoteLoad(arm_patches, ARM_LOAD_POINT, (0, 24, -12))],
            "rama (hacia atrás)": [RemoteLoad(arm_patches, BRANCH_POINT, (-20, 10, 0))],
            "imanes a punto de ceder": [RemoteLoad(bosses, (70, 0, 35), (0, -100, 0)),
                                        RemoteLoad([lug], (0, 0, 35), (0, 100, 0))],
        },
        round=2.0, voxel=3.0, volfrac=0.155,   # ~ la masa de la original rmin=2.5, min_wall=1.2,
        youngs=2100.0, density=1.27e-3,   # PETG
        baseline="baselines/cabeza_fija.stl",
    )


PROBLEMS = {"cabeza_fija": cabeza_fija}
