# Mini15 — bípedo pequeño de 15 motores (simulación MuJoCo)

Bípedo de **~23 cm y ~0.96 kg** con **15 motores**, con proporciones similares al
Microduck: piernas cortas con la rodilla hacia atrás, torso compacto, cuello corto y
una cabeza con cámara y una boca pequeña móvil.

![Mini15 caminando](media/walk.gif)

Esta versión es la **simulación**: el modelo físico más una caminata programada que ya
funciona dentro de los límites reales de los servos. La IA entrenada y las piezas
imprimibles vienen después.

> Proyecto independiente de Pip-Boy Otto; vive en esta carpeta solo de forma temporal.

## Diseño

```
          ┌───────────┐
          │  cabeza ◉ │  cámara; boca pequeña debajo
          └─────┬─────┘
                ┃         cuello corto: 4 micro servos (pitch, pitch, yaw, roll)
            ┌───┸───┐
            │ torso │     batería NP-F550, Raspberry Pi Zero 2W, IMU
            └┬─────┬┘
     cadera  ●     ●      yaw + roll + pitch (3 servos por lado)
            ╱       ╲
     rodilla●       ●     dobla hacia atrás
             ╲     ╱
     tobillo  ●   ●
            ▬▬▬▬ ▬▬▬▬     pies 8 x 4.4 cm con interruptor de contacto
```

| Grupo | Motores | Servo |
|---|---|---|
| Pierna izq. | cadera yaw, cadera roll, cadera pitch, rodilla, tobillo | 5x Feetech STS3215 7.4 V |
| Pierna der. | ídem | 5x Feetech STS3215 7.4 V |
| Cuello/cabeza | cuello pitch, cabeza pitch, cabeza yaw, cabeza roll, boca | 5x micro servo de bus (p. ej. Feetech SCS0009) |

Medidas principales: muslo 4 cm, canilla 4.5 cm, cadera a 8.5 cm del piso
(rodillas flexionadas), cuello 1.6 cm, cabeza 8.4 x 6.4 x 4 cm, boca 2.4 x 2.8 cm.

La distribución de motores sigue la de Open Duck Mini (del mismo autor que trabaja
en el Microduck) más la boca. El Microduck no publica el desglose exacto de sus
15 motores, así que esto es una aproximación.

## Resultados en simulación (caminata programada, sin IA)

| Métrica | Valor |
|---|---|
| Velocidad | ~5.6 cm/s (68 cm en 12 s) |
| Ritmo | 4 pasos por segundo, pasos cortos (como robots de este tamaño) |
| Desvío al ir recto | ~3 cm lateral, ~2° de giro en 12 s |
| Inclinación máx. del torso | ~4° |
| Torque de pierna (percentil 99) | ~1.1 N·m de ~1.9 N·m |
| Velocidad máx. pedida a un servo | ~3.3 rad/s (el STS3215 da ~4.7) |
| Giro | ambos lados, hasta ~110–150° en 10 s (`--turn`, máx. ±0.35) — ver [video](media/turn.mp4) |

Probado también con piso resbaloso (fricción 0.5), pegajoso (1.3), +150 g y servos
más blandos o más rígidos (kp 7 y 15): no se cae en ningún caso.

## Uso

```bash
cd biped
pip install -r requirements.txt
cd sim
python run_demo.py                     # simula e imprime resultados
python run_demo.py --video mini15.mp4  # graba video (en servidor: MUJOCO_GL=osmesa o egl)
python run_demo.py --viewer            # visor 3D interactivo (requiere pantalla)
python run_demo.py --turn 0.3          # gira a la izquierda (negativo = derecha, máx. ±0.35)
python -m pytest -q                    # pruebas
```

Archivos:
- `model/mini15.xml` — el robot (medidas, masas, 15 motores, IMU, cámara, sensores de pie)
- `model/scene.xml` — robot + piso
- `sim/gait.py` — caminata programada con cinemática inversa de las piernas
- `sim/common.py` — cargar modelo, simular y medir
- `sim/run_demo.py` — demo / video / visor
- `sim/test_biped.py` — pruebas

## Lista de piezas estimada

Precios de referencia del BOM de Open Duck Mini; los micro servos y la batería son
estimados y hay que confirmarlos.

| Pieza | Cant. | Aprox. |
|---|---|---|
| Feetech STS3215 **7.4 V** (19 kg·cm) | 10 | 140 € |
| Micro servo de bus con lectura de posición (p. ej. SCS0009) | 5 | 30–50 € |
| Raspberry Pi Zero 2W + microSD | 1 | 36 € |
| Placa Waveshare Bus Servo Adapter (A) | 1 | 5 € |
| IMU BNO055 (o clon) | 1 | 1–40 € |
| Batería NP-F550 (7.4 V) + soporte + regulador 5 V + interruptor | 1 | 25–35 € |
| Cámara Raspberry Pi | 1 | 5–25 € |
| Interruptores de pie SS-10 | 2–4 | 2–4 € |
| Insertos M3, tornillos, PLA, TPU para suelas | — | ~15 € |
| **Total** | | **~260–350 €** |

## Limitaciones (importante)

- **Servos:** las ganancias (`kp`, `kv`, `armature`, fricción) son estimadas. Antes de
  pasar al robot real hay que medirlas con un servo real (p. ej. con
  [BAM](https://github.com/Rhoban/bam), como hace Open Duck).
- **Peso:** ~0.96 kg, más que el Microduck (~0.8 kg), porque el STS3215 es grande
  para este tamaño. Servos más chicos bajarían el peso.
- **Micro servos de cabeza:** verificar voltaje y protocolo; pueden necesitar un
  regulador o bus aparte.
- **Paso bajo** (~0.5 cm): sirve para piso plano, no para alfombras ni rampas.
- **Sin tobillo roll** (igual que Open Duck): por eso la caminata usa pasos cortos y
  rápidos en vez de balancearse mucho de lado a lado.
- **Cuello corto:** los 4 micro servos del cuello tienen que ir muy juntos; al diseñar
  las piezas puede que haga falta quitar uno (p. ej. cabeza roll).
- **Caminata programada:** no reacciona a empujones ni a obstáculos. Eso es lo que
  resuelve el entrenamiento con IA (como en el video de NVIDIA).
- Las piernas no chocan entre sí en la simulación.

## Próximos pasos

1. **Entrenamiento con IA (RL):** entorno sobre este modelo (IMU, sensores de pie y
   cámara ya están definidos) para que camine reaccionando a empujones, suba rampas
   y esquive obstáculos.
2. **Piezas imprimibles:** torso, soportes de cadera, muslos, canillas, pies y cabeza
   en OpenSCAD con las mismas medidas del modelo.
3. **Software del robot:** correr la caminata (o la política entrenada) en la
   Raspberry Pi Zero 2W a 50 Hz.
