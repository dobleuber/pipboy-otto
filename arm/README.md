# Brazo con cámara (SO-101): simulación en la mesa y en el morral

Un brazo **SO-101** (6 servos Feetech STS3215, proyecto LeRobot) con cámara en la muñeca que
**ve, reacciona y sostiene cosas**. Simulado primero en la mesa y después en el morral, sobre el
hombro, mientras la persona camina.

> Proyecto independiente de Pip-Boy Otto; vive en esta carpeta solo de forma temporal.

El modelo del brazo es el oficial de [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/robotstudio_so101)
(Apache 2.0). No está copiado en el repo: se descarga solo la primera vez, en `third_party/`.

## Demo 1: buscar, saludar y seguir a una persona

[Video](media/seguir_persona.mp4). El brazo **solo usa la imagen de su cámara** (un detector de
piel simple, en lugar de un detector de caras) y sus propios ángulos, como el robot real:

- **buscar:** gira de lado a lado hasta ver una cara;
- **saludar:** asiente con la muñeca al encontrarla;
- **seguir:** la mantiene en el centro de la imagen, con el horizonte nivelado.

La persona se mueve, se acerca, se levanta, se va de la habitación y vuelve por el otro lado.

| Resultado | |
|---|---|
| Error de mirada al seguir | mediana **2.7°**, p90 6.3° |
| Saludos | 2 (al empezar y cuando vuelve) |
| Torque máximo | **1.17 N·m** (alcanzan los servos de 7.4 V, límite 1.91 N·m) |

## Demo 2: agarrar, mostrar, sostener y devolver

[Video](media/agarrar_y_sostener.mp4). Secuencia programada con cinemática inversa: baja con la
pinza vertical, agarra el cubo, se lo muestra a la persona (30 cm adelante, 24 cm de alto), lo
sostiene 4 s y lo devuelve a la mesa.

Cuánto peso aguanta en la pose de "mostrar" (torque del servo más cargado al sostener):

| Peso | Servos de 7.4 V (1.91 N·m) | Servos de 12 V (2.94 N·m) |
|---|---|---|
| 30 g | 0.56 N·m ✔ | 0.56 N·m ✔ |
| 100 g | 0.76 ✔ | 0.77 ✔ |
| 200 g | 1.05 ✔ | 1.05 ✔ |
| 300 g | 1.34 ✔ | 1.36 ✔ |
| 400 g | 1.64 ✔ (86 %, al límite) | 1.67 ✔ |
| 600 g | ✘ se le cae | 2.26 ✔ (77 %) |

Para sostener **un rato** conviene quedarse por debajo de ~50 % del torque máximo (los servos se
calientan): **~150 g con 7.4 V** y **~300 g con 12 V** con el brazo así de estirado. Más cerca
del cuerpo, aguanta bastante más.

## Demo 3: en el morral, sobre el hombro, caminando

[Video mirando](media/morral_mirar.mp4) · [video sosteniendo](media/morral_sostener.mp4)

El brazo va en un soporte sobre el hombro derecho del morral. La persona camina por una vereda
a 4.3 km/h con el vaivén real de la marcha (sube y baja ~2 cm a 1.8 pasos/s, se balancea y gira
un poco). El morral está "soldado" al cuerpo con un resorte rígido, así que el brazo recibe las
aceleraciones de verdad. Hay tres personas en la vereda.

**Dónde va el soporte:** en el borde del hombro (26 cm al costado del centro de la cabeza), a
la altura de los hombros. Más adentro, el brazo queda a menos de 10 cm de la cabeza.

**Seguridad (siempre activa):** la base no gira hacia la cabeza, y si alguna parte del brazo
queda a menos de 10 cm de ella, el brazo vuelve a la postura de reposo. En la prueba, lo más
cerca que estuvo fueron 9.8 cm.

### Mirar a la gente mientras caminas

| Error de mirada (mediana / p90) | Sin predicción | Con predicción |
|---|---|---|
| Sin IMU | 8.6° / 22.6° | 3.6° / 14.0° |
| **Con IMU** | 10.8° / 22.0° | **2.8° / 7.2°** |

- **IMU en el soporte** (BNO055): mide el vaivén y los servos lo compensan.
- **Predicción:** con dos detecciones seguidas se estima hacia dónde se mueve la persona en la
  imagen. Al pasar caminando junto a alguien, su dirección gira rápido (~0.7 rad/s) y sin esto
  la mirada va atrasada.
- Con las dos, caminando se mira casi tan bien como parado (2.8°). Torque máximo 1.36 N·m:
  alcanzan los servos de 7.4 V.

### Sostener algo mientras caminas

Una caja de 4 x 4 x 6 cm sostenida a la altura del pecho y la cara, 28 cm adelante del hombro,
durante 17 s caminando. **Decisión:** el brazo nunca sostiene el celular (se puede caer o lo
pueden robar); solo cosas livianas y sin valor, como una botella chica o una linterna.

| Peso | Torque (servo más cargado) | Se deslizó | Fuerza / momento en el soporte |
|---|---|---|---|
| 50 g | 0.6 N·m | 3 mm | 9 N / 1.3 N·m |
| 100 g | 0.76 | 3 mm | 10 N / 1.5 N·m |
| 200 g | 1.08 | 5 mm | 11 N / 1.9 N·m |
| 300 g | 1.40 | 6 mm | 13 N / 2.4 N·m |
| 400 g | 1.73 | 7 mm | 14 N / 2.8 N·m |
| 500 g | 1.91 con 7.4 V (al límite) · 2.06 con 12 V | 7–8 mm | 16 N / 3.3 N·m |

- Para sostener un rato (menos de ~50 % del torque máximo): **~150 g con 7.4 V** y **~300 g con
  12 V**.
- La caja se sacude ~3.5 m/s² (un tercio de la gravedad) por el vaivén de la marcha.
- **El soporte** tiene que aguantar ~16 N y ~3.3 N·m en el peor caso: con margen, diseñarlo para
  **6–7 N·m**.

## Lo que aprendimos al simular

- La cámara de muñeca va montada a ~30° de la pinza y del lado: la postura de reposo tiene que
  dejarla derecha (giro de muñeca −90°) o la imagen sale de cabeza.
- **Limitar la aceleración** de los servos (10 rad/s²) bajó el torque máximo de 2.94 a 1.17 N·m:
  los picos venían de arranques bruscos, no del peso.
- **La pinza no debe apretar con todo**: se limitó a ~0.8 N·m (~10 N de apriete). Con todo el
  torque aplasta el objeto contra la palma y lo suelta.
- Con la pinza vertical y en alto, la muñeca llega a su tope: conviene agarrar desde arriba y
  mostrar el objeto de frente.

## Uso

```bash
cd arm/sim
pip install mujoco numpy pillow imageio imageio-ffmpeg pytest
python demo_track.py                       # buscar / saludar / seguir (imprime resultados)
python demo_track.py --video seguir.mp4    # con video
python demo_hold.py --mass 0.2 --volts 7.4V --video sostener.mp4
python demo_walk.py                        # en el morral: mirar caminando (con y sin IMU)
python demo_walk.py --hold                 # en el morral: sostener caminando (pesos y voltajes)
python -m pytest -q                        # pruebas (10)
```

En un servidor sin pantalla, anteponer `MUJOCO_GL=osmesa` (o `egl`).

Archivos:
- `sim/scene.py` — descarga el modelo, arma la mesa, objetos y la persona
- `sim/control.py` — cinemática inversa, seguimiento con la cámara, detector
- `sim/demo_track.py`, `sim/demo_hold.py` — los demos de la mesa
- `sim/backpack.py` — escena del morral: usuario que camina, soporte, IMU, vereda con gente
- `sim/demo_walk.py` — demos del morral (mirar y sostener caminando, seguridad)
- `sim/test_arm.py` — pruebas

## Próximos pasos

1. **Más realismo:** detector de caras real (p. ej. el de MediaPipe o un YOLO en la NPU de la
   Orange Pi 5 Pro) sobre la imagen simulada, y agarrar objetos ubicados con la cámara.
2. **Voz:** preguntas y respuestas con un modelo de visión y lenguaje usando la imagen de la cámara.
3. **Diseñar el soporte del morral** (6–7 N·m) y la caja de batería y placa.
4. **Lista de compras** (SO-101 con servos de 12 V, IMU, cámara, micrófono, parlante, batería).
