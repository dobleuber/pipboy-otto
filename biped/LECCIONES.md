# Qué aprender de Microduck y Open Duck

Comparación hecha con sus repositorios (modelo MJCF, constantes y guía de entrenamiento del
Microduck; documentación sim2real de Open Duck), no de memoria.

## Reparto de la masa: la diferencia principal

| | Microduck (modelo) | Mini16 (nuestro CAD) |
|---|---|---|
| Masa total | 737 g (~800 g real) | 1182 g |
| Altura | ~25 cm | ~32 cm |
| Servos | 14 XL330 (~18 g) | 12 STS3215 (55 g) + 4 SCS0009 |
| **Piernas** | **35 %** (129 g c/u) | **62 %** |
| Torso | 27 % (199 g) | ~30 % |
| **Cuello + cabeza** | **38 %** (cabeza sola 189 g) | **8 %** |
| Motores por pierna | 5 (sin tobillo roll) | 6 |

Microduck tiene piernas livianas y casi 40 % de la masa arriba, en una cabeza móvil. Con esa
cabeza el robot se equilibra: moverla corre el centro de masa sin mover las piernas. En Mini16
pasa lo contrario. Las piernas pesan tanto que cada paso mueve casi todo el robot, y para
compensarlo agregué el tobillo roll, que suma otros dos servos pesados.

## Lecciones

1. **Servos chicos en las piernas.** Un XL330 pesa un tercio de un STS3215. Open Duck usa
   STS3215, pero mide 42 cm: los servos grandes piden un robot grande.
2. **5 motores por pierna bastan** si el equilibrio lo hace el control, no la mecánica. Ninguno
   de los dos tiene tobillo roll.
3. **Cabeza pesada y móvil (4 articulaciones)** como contrapeso. La batería o la placa pueden
   ir en la cabeza para darle masa útil.
4. **Postura de reposo:** rodillas casi rectas, cadera pitch −26°, tobillo +26°. El torso está
   corrido 5 mm adelante para que el centro de masa quede sobre el eje del tobillo.
5. **El equilibrio lo da la IA, no una caminata programada.** Open Duck imita una caminata de
   referencia (estilo Disney BDX) y la IA aprende a corregirla. Microduck entrena PPO con 4096
   simulaciones en paralelo en GPU, 1–2 h.
6. **Modelo fiel de los motores (BAM)** y variaciones en la simulación: voltaje de batería,
   retardo, fricción, juego de ±1° en los engranajes. Open Duck publica los parámetros BAM del
   STS3215 a 7.4 V.
7. **Evaluar diseños con IA.** Mi error fue comparar diseños con la caminata programada, que
   favorece al tobillo roll. Con IA, el diseño de 5 motores y cabeza pesada probablemente gana.

## Direcciones posibles

- **A. Estilo Microduck:** servos chicos (XL330 o un Feetech equivalente) en las piernas, 5 por
  pierna, cabeza pesada con 4 articulaciones, ~25 cm y ~800 g.
- **B. Estilo Open Duck:** mantener los STS3215, 5 por pierna, y escalar a ~40 cm con cabeza
  pesada.

En los dos casos: modelar el motor con BAM y entrenar con IA en la GPU NVIDIA (entrenamiento
corto, 30–60 min), en vez de afinar a mano una caminata programada.
