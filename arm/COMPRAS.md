# Lista de compras: brazo SO-101 con cámara (mesa → morral → voz)

Por fases: cada una ya funciona por sí sola. Precios aproximados en euros (octubre de 2026);
varían mucho según la tienda, el envío y los impuestos: confirmar antes de comprar.

Ya tienes: **Orange Pi 5 Pro** (el cerebro), una impresora 3D (supuesto) y una PC con NVIDIA
(para entrenar más adelante).

## Fase 1: el brazo en la mesa (~250 €)

| Cant. | Qué | Precio aprox. | Notas |
|---|---|---|---|
| 6 | Servo **Feetech STS3215-C018** (12 V, 30 kg·cm, engranaje 1/345) | ~28 € c/u | el brazo "seguidor" del SO-101. La versión de 7.4 V (C001, ~25 €) alcanza para mirar y seguir caras; la de 12 V da margen para sostener cosas |
| 1 | Placa de servos **Waveshare Bus Servo Adapter (A)** | ~5–12 € | USB ↔ bus de los servos (la que usa el SO-101) |
| 1 | Fuente de **12 V / 5 A** (conector redondo 5.5 x 2.1) | ~12 € | para usarlo en la mesa |
| 1 | Cámara **USB UVC de 32 x 32 mm** (gran angular) | ~15–25 € | va en la muñeca (el modelo del SO-101 ya trae el soporte) |
| 1 | Filamento **PETG 1 kg** | ~20 € | piezas del SO-101 (~0.4 kg) + bandeja, receptor y base de mesa |
| 2 | Prensas en C | ~10 € | para la base de mesa |
| — | Disipador con ventilador para la Orange Pi 5 Pro, tarjeta microSD o eMMC, cable USB | ~15 € | si no los tienes |

Alternativa: los kits "SO-ARM101" de Seeed, WowRobo y otros traen los servos, la placa y la
fuente juntos (algunos con piezas impresas y cámara). Comparar precio con la lista de arriba.

## Fase 2: el morral (~150 €)

| Cant. | Qué | Precio aprox. | Notas |
|---|---|---|---|
| 3 | Celdas **18650 Molicel P30B** (o similar de alta descarga) | ~5 € c/u | batería 3S = 11.1 V (12.6 V cargada) para los servos de 12 V |
| 1 | Portapilas 3 x 18650 + **BMS 3S de 20 A** | ~8 € | protección y balanceo |
| 1 | Cargador 3S con balanceo | ~25 € | |
| 1 | Convertidor **12 V → 5 V / 5 A** (USB-C o bornes) | ~8 € | la Orange Pi 5 Pro pide 5 V / 4 A |
| 1 | **IMU BNO085** (o BNO055) | ~20–30 € | en la bandeja, bajo la base del brazo (compensa el vaivén) |
| 1 | **Botón de parada de emergencia** (hongo, con enclavamiento) | ~8 € | en la correa del hombro |
| 1 | Módulo **MOSFET de 15 A** (o relé de 12 V / 10 A) | ~4 € | el botón corta la alimentación de los servos |
| 1 | Sensor **Hall A3144** | ~1 € | en la bisagra: detecta si el brazo se dobló |
| 1 | Portafusible + fusible de 7.5 A, conectores XT60 | ~6 € | |
| 1 | Bolsa ignífuga para baterías | ~8 € | la batería va dentro de la caja |
| 1 | Tubo de aluminio cuadrado 20 x 20 x 1.5 mm (cortar a 142 mm) | ~6 € | ferretería |
| 1 | Placa de HDPE o PP de 3 mm, 25 x 38 cm | ~10 € | o una tabla de picar de plástico |
| 8 | Imanes de neodimio N52, 10 x 5 mm | ~6 € | bisagra (se pegan con epoxi) |
| 1 | Tornillo M8 x 70 + tuerca autoblocante + 2 arandelas de nylon | ~3 € | pasador de la bisagra |
| — | Surtido de tornillos M5 (12–30 mm), tuercas y arandelas; 1 tornillo M4 x 10 | ~10 € | |
| — | Goma o TPU de 1 mm, epoxi, precintos, cable de silicona 18 AWG | ~10 € | |

Más el morral: cualquiera con **bolsillo para laptop, correa de pecho y cinturón de cadera**.

## Fase 3: voz (~40 €)

| Cant. | Qué | Precio aprox. | Notas |
|---|---|---|---|
| 1 | Micrófono USB chico (o un arreglo de micrófonos tipo ReSpeaker) | ~10–30 € | el arreglo oye mejor con ruido de calle |
| 1 | Parlante chico + amplificador I2S MAX98357 (o parlante USB) | ~10–15 € | |

Las respuestas las da un modelo de visión y lenguaje en la nube (con el hotspot del celular) o
uno chico en la Orange Pi 5 Pro: se decide en esa fase.

## Opcional: brazo "líder" para enseñarle tareas (~120 €)

Para el aprendizaje por imitación de LeRobot (mueves el líder con la mano y el seguidor copia):
6 servos STS3215 de 7.4 V con engranajes distintos según la articulación (ver la guía del
SO-101) + otra placa Waveshare. Se puede dejar para después.

## Resumen

| Fase | Aprox. |
|---|---|
| 1. Mesa | ~250 € |
| 2. Morral | ~150 € (+ el morral) |
| 3. Voz | ~40 € |
| Opcional: líder | ~120 € |
| **Total sin el líder** | **~440 €** |

## Antes de comprar

- Decidir **7.4 V o 12 V** para los servos (no se mezclan en el mismo bus): 12 V es lo que
  recomiendo por el margen, y con eso la batería del morral es 3S.
- Imprimir las **probetas del riel** (`cad/stl/probeta_*.stl`) y medir la base del SO-101.
