# Brazo con cámara (SO-101): simulación en la mesa

Primer paso del proyecto: un brazo **SO-101** (6 servos Feetech STS3215, proyecto LeRobot) con
cámara en la muñeca que **ve, reacciona y sostiene cosas**. Primero en la mesa; si funciona, se
pasa al morral, sobre el hombro.

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
calientan): **~150 g con 7.4 V** y **~300 g con 12 V** con el brazo así de estirado. Un celular
(~200 g) pide la versión de 12 V. Más cerca del cuerpo, aguanta bastante más.

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
python -m pytest -q                        # pruebas (6)
```

En un servidor sin pantalla, anteponer `MUJOCO_GL=osmesa` (o `egl`).

Archivos:
- `sim/scene.py` — descarga el modelo, arma la mesa, objetos y la persona
- `sim/control.py` — cinemática inversa, seguimiento con la cámara, detector
- `sim/demo_track.py`, `sim/demo_hold.py` — los dos demos
- `sim/test_arm.py` — pruebas

## Próximos pasos

1. **Más realismo:** detector de caras real (p. ej. el de MediaPipe o un YOLO en la NPU de la
   Orange Pi 5 Pro) sobre la imagen simulada, y agarrar objetos ubicados con la cámara.
2. **Voz:** preguntas y respuestas con un modelo de visión y lenguaje usando la imagen de la cámara.
3. **Al morral:** simular el brazo sobre el hombro con el movimiento de una persona caminando,
   medir sacudidas y torques, y diseñar el soporte.
4. **Lista de compras** (SO-101 con servos de 12 V, cámara, micrófono, parlante, fuente).
