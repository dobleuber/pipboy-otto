# Mini17 — bípedo pequeño de 17 motores (simulación MuJoCo + entrenamiento con IA)

Bípedo de **~23 cm y ~1.07 kg** con **17 motores**, con proporciones similares al
Microduck: piernas cortas con la rodilla hacia atrás, tobillo con dos ejes, torso
compacto, cuello corto y una cabeza con cámara y una boca pequeña móvil.

![Mini17 caminando](media/walk.gif)

Incluye el modelo físico, una caminata programada que respeta los límites reales de
los servos, terrenos de prueba (rampas y escalones) y un entorno para entrenarlo con IA.

> Proyecto independiente de Pip-Boy Otto; vive en esta carpeta solo de forma temporal.

## Diseño

```
          ┌───────────┐
          │  cabeza ◉ │  cámara; boca pequeña debajo
          └─────┬─────┘
                ┃         cuello corto: 4 micro servos (pitch, pitch, yaw, roll)
            ┌───┸───┐
            │ torso │     batería NP-F550, placa (ver abajo), IMU
            └┬─────┬┘
     cadera  ●     ●      yaw + roll + pitch (3 servos por lado)
            ╱       ╲
     rodilla●       ●     dobla hacia atrás
             ╲     ╱
     tobillo  ◆   ◆       pitch + roll (2 servos por lado)
            ▬▬▬▬ ▬▬▬▬     pies 8 x 4.4 cm con interruptor de contacto
```

| Grupo | Motores | Servo |
|---|---|---|
| Pierna izq. | cadera yaw, cadera roll, cadera pitch, rodilla, tobillo pitch, tobillo roll | 6x Feetech STS3215 7.4 V |
| Pierna der. | ídem | 6x Feetech STS3215 7.4 V |
| Cuello/cabeza | cuello pitch, cabeza pitch, cabeza yaw, cabeza roll, boca | 5x micro servo de bus (p. ej. Feetech SCS0009) |

Medidas principales: muslo 4 cm, canilla 4.5 cm, cadera a 8.5 cm del piso
(rodillas flexionadas), cuello 1.6 cm, cabeza 8.4 x 6.4 x 4 cm, boca 2.4 x 2.8 cm.

**Por qué 17 motores:** la versión de 15 (como Open Duck Mini) no tiene tobillo roll; al
cargar el peso en una pierna el pie se inclina, así que solo podía arrastrar los pies.
Con el tobillo roll el pie queda plano y puede levantarlo 2 cm.

## Caminata programada (sin IA)

| Métrica | Valor |
|---|---|
| Velocidad | ~4 cm/s (48 cm en 12 s) |
| Altura de paso | 2 cm |
| Desvío al ir recto | ~2 cm lateral, <1° de giro en 12 s |
| Giro | ~150° en 10 s hacia cada lado (`--turn 0.3`) — ver [video](media/turn.mp4) |
| Torque de pierna (percentil 99) | ~0.94 N·m de ~1.9 N·m |
| Velocidad máx. pedida a un servo | ~4.0 rad/s (el STS3215 da ~4.7) |

No se cae con piso resbaloso (fricción 0.5), pegajoso (1.3), +150 g ni con servos más
blandos o rígidos (kp 7 y 15).

## Rampas y escalones

Comparación de variantes con caminata programada (`sim/terrain.py`):

| Variante | Rampa 10° | Rampa 15° | Escalón 1 cm |
|---|---|---|---|
| 15 motores (sin tobillo roll) | trabado | se cae | trabado |
| 16 motores (+ cintura roll) | lento | se cae | se cae |
| **17 motores (+ tobillo roll)** | **sube** | **sube** | se cae |

La cintura ayuda poco: solo ~30 % del peso está arriba de ella. Ninguna caminata fija
pasa escalones de 1 cm o más: hay que reaccionar al borde, y para eso es la IA.

## Entrenamiento con IA (`rl/`)

La IA no aprende a caminar desde cero: aprende **correcciones** sobre la caminata
programada. Ve lo mismo que vería el robot real: IMU, posición y velocidad de los
motores, contacto de los pies y un **sensor de distancia hacia el piso de adelante**
(como el ToF del Microduck) para "ver" escalones.

Cada episodio cambia al azar: terreno (plano, rampas 5–20°, escalones 0.5–2 cm),
fricción, peso, rigidez de los servos, retardo de control y empujones. La velocidad
de los servos se limita a la del STS3215.

```bash
cd biped
pip install -r requirements-rl.txt
cd rl
python train.py --steps 5000000 --envs 8 --out runs/mix   # entrenar
python evaluate.py --policy runs/mix/policy.zip --video videos   # comparar + videos
python export_onnx.py runs/mix/policy.zip mini17_policy.onnx     # para el robot
python -m pytest -q                                        # pruebas del entorno
```

Resultados (5 semillas por terreno, con variaciones aleatorias y empujones; éxito = no
se cae y avanza ≥30 cm):

| Terreno | Caminata programada | Con IA (0.5 M pasos, prueba corta) |
|---|---|---|
| Plano | 100 % | 100 % |
| Rampa 5° | 100 % | 80 % |
| Rampa 10° | 100 % | 60 % |
| Rampa 15° | 0 % (11 cm) | 0 % (27 cm) |
| Rampa 20° | 0 % | 0 % |
| Escalones 0.5 cm | 100 % | 100 % |
| Escalones 1–2 cm | 0 % | 0 % |

Con solo 0.5 M pasos (8 min en CPU) la IA todavía no supera a la caminata programada:
avanza más en 15° pero se volvió más cautelosa en rampas suaves. Es una prueba de que
el sistema funciona, no un resultado final.

**Dónde entrenar en serio:** en una PC con tarjeta NVIDIA.
- Rápido de usar: este mismo `train.py` en la CPU de la PC, subiendo `--envs` al número
  de núcleos (escala casi en proporción). Típicamente 5–20 M pasos.
- Mucho más rápido: pasar el entorno a simulación en GPU (p. ej.
  [mjlab](https://github.com/mujocolab/mjlab), que es lo que usa `microduck_rl`, o
  MuJoCo Playground) para entrenar miles de robots en paralelo, como en el video de
  NVIDIA. El modelo MJCF sirve directo.

## Placa para el robot

La política entrenada es una red chica (2 capas de 128): cualquier placa la corre a
50 Hz. El límite es el **tamaño**: el torso mide ~6 x 8 x 4.4 cm.

| Placa | ¿Cabe? | Notas |
|---|---|---|
| Orange Pi Zero 3 | sí, justo (~5 x 5.5 cm) | buena opción; sin conector de cámara: usar cámara USB |
| Orange Pi Zero 2 | sí, justo | similar a la Zero 3, algo más antigua |
| Raspberry Pi Zero 2W | sí (6.5 x 3 cm) | la más fácil de meter; tiene conector de cámara CSI |
| Orange Pi 5 Pro | no (8.9 x 5.6 cm) | potente (NPU), pero exige un torso más grande y más batería |

## Uso de la simulación

```bash
cd biped
pip install -r requirements.txt
cd sim
python run_demo.py                     # simula e imprime resultados
python run_demo.py --video mini17.mp4  # graba video (en servidor: MUJOCO_GL=osmesa o egl)
python run_demo.py --viewer            # visor 3D interactivo (requiere pantalla)
python run_demo.py --turn 0.3          # gira a la izquierda (negativo = derecha)
python -m pytest -q                    # pruebas
```

Archivos:
- `model/mini17.xml` — el robot (medidas, masas, 17 motores, IMU, cámara, sensores de pie)
- `model/scene.xml` — robot + piso
- `sim/gait.py` — caminata programada con cinemática inversa de las piernas
- `sim/common.py` — cargar modelo, simular y medir
- `sim/terrain.py` — rampas y escalones de prueba
- `sim/run_demo.py` — demo / video / visor
- `rl/env.py`, `rl/train.py`, `rl/evaluate.py`, `rl/export_onnx.py` — entrenamiento con IA

## Lista de piezas estimada

Precios de referencia del BOM de Open Duck Mini; los micro servos y la batería son
estimados y hay que confirmarlos.

| Pieza | Cant. | Aprox. |
|---|---|---|
| Feetech STS3215 **7.4 V** (19 kg·cm) | 12 | 170 € |
| Micro servo de bus con lectura de posición (p. ej. SCS0009) | 5 | 30–50 € |
| Placa (Orange Pi Zero 3 / Raspberry Pi Zero 2W) + microSD | 1 | ya la tienes |
| Placa Waveshare Bus Servo Adapter (A) | 1 | 5 € |
| IMU BNO055 (o clon) | 1 | 1–40 € |
| Sensor de distancia ToF (p. ej. VL53L5CX / VL53L8CX) | 1 | 10–20 € |
| Batería NP-F550 (7.4 V) + soporte + regulador 5 V + interruptor | 1 | 25–35 € |
| Cámara (USB o CSI según la placa) | 1 | 5–25 € |
| Interruptores de pie SS-10 | 2–4 | 2–4 € |
| Insertos M3, tornillos, PLA, TPU para suelas | — | ~15 € |
| **Total (sin placa)** | | **~265–365 €** |

## Limitaciones (importante)

- **Servos:** las ganancias (`kp`, `kv`, `armature`, fricción) son estimadas. Antes de
  pasar al robot real hay que medirlas con un servo real (p. ej. con
  [BAM](https://github.com/Rhoban/bam), como hace Open Duck).
- **Peso:** ~1.07 kg, más que el Microduck (~0.8 kg), porque el STS3215 es grande
  para este tamaño.
- **Tobillo:** los dos servos del tobillo (pitch y roll) tienen que caber en ~2 cm
  sobre la suela; al diseñar las piezas puede que haya que subir un poco el tobillo.
- **Micro servos de cabeza:** verificar voltaje y protocolo; pueden necesitar un
  regulador o bus aparte.
- **Cuello corto:** los 4 micro servos del cuello van muy juntos; puede que haga falta
  quitar uno (p. ej. cabeza roll).
- **IA:** el entrenamiento incluido es corto; falta entrenar en serio (ver arriba).
- Las piernas no chocan entre sí en la simulación.

## Próximos pasos

1. **Entrenar en tu PC con NVIDIA** (más pasos, o pasar a simulación en GPU).
2. **Piezas imprimibles:** torso, caderas, muslos, canillas, tobillos, pies y cabeza
   en OpenSCAD con las mismas medidas del modelo.
3. **Software del robot:** correr la caminata y la política ONNX en la placa a 50 Hz.
