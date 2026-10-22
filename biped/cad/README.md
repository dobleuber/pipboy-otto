# CAD de Mini16 (OpenSCAD)

Piezas imprimibles de la pierna, diseñadas con las medidas del plano oficial del
**Feetech STS3215** (cuerpo 45.22 x 24.72 x 32 mm, eje a 10.11 mm de un extremo, discos de
Ø19.2 mm a ambos lados con 4 agujeros M2 en Ø14 mm, agujeros M2 de carcasa a 20.5 mm).

Estado: **pierna completa** (izquierda y derecha). Falta: torso y cabeza.

## Piezas por pierna

| Pieza | Material | Relleno | Masa aprox. | Qué hace |
|---|---|---|---|---|
| `yaw_link` | PETG | 35 % | 7 g | atornillada al disco del servo de cadera yaw; "U" sobre el servo de cadera roll |
| `roll_link` | PETG | 35 % | 14 g | sostiene el servo roll (acostado hacia afuera) y el pitch (acostado hacia adelante) |
| `thigh` | PETG | 35 % | 13 g | "U" sobre el servo de cadera pitch; cuna del servo de rodilla (acostado hacia atrás) |
| `shin` | PETG | 35 % | 13 g | "U" sobre la rodilla; cuna del servo de tobillo pitch (acostado hacia adelante) |
| `ankle_cross` | PETG | 35 % | 13 g | "U" sobre el tobillo pitch; cuna del servo de tobillo roll (acostado hacia afuera) |
| `foot` | PETG | 35 % | 19 g | "U" sobre el tobillo roll; plancha con alojamientos para 2 sensores de pisada |
| `sole` | **TPU 95A** | 40 % | 8 g | suela con bordes curvos (punta, talón y costados) |

Pierna derecha: mismas piezas en espejo (`right_*.stl`). Total de plástico: ~89 g por pierna.

**Impresión:** 4 perímetros (0.4 mm), capa 0.2 mm, sin soportes en lo posible (las placas
planas hacia la cama). Holgura de ajuste `CL = 0.4 mm` en `lib/params.scad`: bajarla a 0.3 si la
impresora es precisa.

## Distancias entre ejes (las usa la simulación)

| Tramo | mm |
|---|---|
| Disco de cadera yaw → eje roll | 25.0 |
| Eje roll → eje pitch | 28.2 |
| Muslo (pitch → rodilla) | 33.3 |
| Canilla (rodilla → tobillo pitch) | 33.3 (56.1 con `SHIN_SERVO = "up"`) |
| Tobillo pitch → tobillo roll | 33.3 |
| Tobillo roll → suela | 34.5 |
| Separación de cada pierna al centro | 30.0 |

Rangos sin choques (revisados con `check_leg.py`): cadera yaw ±34°, cadera roll ±29°,
cadera pitch −14° a 74°, rodilla −83° a 6°, tobillo −11° a 80°, tobillo roll ±29°
(con `SHIN_SERVO = "up"`: rodilla hasta −100° y tobillo ±80°, a cambio de 23 mm más de canilla).
La caminata usada en la simulación no provoca choques entre piezas, ni entre las dos piernas.

## Tornillería (por pierna)

- Discos de servo: 4x M2 por disco (2 discos por servo sujetado en "U"); tornillo central M3
  del servo.
- Carcasas de servo: tornillos M2 autorroscantes a los agujeros del servo.
- Suela a pie: 4x M3 x 8 + 4 insertos M3 de latón (agujero Ø4.0, 5 mm).
- Sensores de pisada: 2 microinterruptores con pernos Ø2 (**medir el modelo comprado** y
  ajustar `SW_*` en `lib/params.scad`).
- Fijador de roscas azul 243 solo en uniones metal-metal (tornillo central del disco).

Nota: el STS3215 ya trae eje pasivo con rodamiento propio, por eso las piezas sujetan el servo
por sus dos discos y no hace falta un rodamiento impreso.

## Flujo de trabajo

```bash
./export.sh            # piezas -> stl/ (izquierda, derecha y servos)
python check_leg.py    # revisa choques en todo el rango (y --gait: con la caminata)
python build_mjcf.py   # regenera model/mini16.xml con estas medidas, mallas y masas
```

`lib/params.scad` es la única fuente de las medidas: al cambiar algo ahí, correr los tres pasos.
