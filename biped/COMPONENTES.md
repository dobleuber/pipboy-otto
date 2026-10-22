# Componentes de Mini16

Decisiones tomadas: **Orange Pi Zero 3 + cámara USB**, **2x 18650 de alta descarga**,
**Feetech SCS0009 en la cabeza**, **sensor ToF VL53L5CX/VL53L8CX** y **4 sensores de pisada**.
Todo esto ya está reflejado en el modelo de simulación (`model/mini16.xml`).

## Lista

| Cant. | Componente | Datos clave | Masa | Precio aprox. | Notas |
|---|---|---|---|---|---|
| 12 | Feetech **STS3215 7.4 V** | 19.5 kg·cm, bus TTL, encoder magnético, 45.2 x 24.7 x 35 mm | 55 g c/u | ~14 € c/u | piernas; corriente de bloqueo 2–2.5 A c/u |
| 4 | Feetech **SCS0009** | 2.3 kg·cm a 6 V, 4–7.4 V, bus TTL, 23.2 x 12.1 x 25.25 mm | 11–13 g c/u | a confirmar | cuello y cabeza; **no** se pueden alimentar directo de la batería |
| 1 | **Orange Pi Zero 3** | H618 4 núcleos, hasta 4 GB, Wi-Fi, ~50 x 55 mm, entrada 5 V | ~25 g (est.) | ya la tienes | sin conector de cámara: cámara por USB |
| 1 | Cámara **USB (UVC)** compacta | placa ~32 x 32 mm, ~70° de campo | ~6 g | 10–20 € | va al frente de la cabeza |
| 2 | Celda **18650 alta descarga** (p. ej. Molicel P30B) | 3000 mAh, 30 A | ~46 g c/u | ~5 € c/u | en serie (2S = 7.4 V nominal, 8.4 V cargada) |
| 1 | Soporte 2x18650 + **BMS 2S** (≥ 15 A) | protección de carga/descarga y balanceo | ~10 g | ~13 € | |
| 1 | Interruptor + conector XT30 | | ~5 g | ~6 € | |
| 1 | **UBEC 5 V / 3 A** | para la Orange Pi y los sensores | ~10 g | ~4 € | |
| 1 | **Regulador buck 6 V / ≥ 3 A** | para los 4 SCS0009 | ~5 g | 3–5 € | |
| 1–2 | Condensador electrolítico **1000–2200 µF / 16 V** | junto a la entrada de potencia de los servos | ~3 g | ~1 € | |
| 2 | Adaptador de bus de servos (Waveshare Bus Servo Adapter A) | USB o UART ↔ bus TTL semidúplex | ~8 g c/u | ~5 € c/u | uno para las piernas (7.4 V) y otro para la cabeza (6 V) |
| 1 | IMU **BNO055** | fusión de sensores a bordo, I2C o UART | ~3 g | 1–40 € | montada nivelada entre las caderas |
| 1 | Sensor ToF **VL53L5CX o VL53L8CX** | matriz 8x8 de distancias, I2C | ~2 g | 15–25 € | al frente del torso, mirando 45° hacia el piso |
| 4 | Microinterruptor **SS-10** | sensor de pisada (punta y talón de cada pie) | ~1 g c/u | ~1 € c/u | alternativa: sensores FSR |
| — | Mecánica | rodamientos 683ZZ / MR105ZZ, insertos M3 de latón, tornillos M2/M3, PETG o PLA, TPU 95A | — | ~25 € | |
| 1 | Cargador 2S con balanceo (o módulo de carga USB-C 2S) | | — | 5–25 € | |

**Total aproximado (sin la placa):** ~270–330 €.

## Cómo se conecta

```
2x 18650 (2S) ─ BMS 2S ─ interruptor ─┬─ condensador ─ adaptador bus #1 ─┬─ pierna izq. (6x STS3215)
                                      │   (7.4 V directo)                 └─ pierna der. (6x STS3215)
                                      ├─ buck 6 V ─ adaptador bus #2 ─ 4x SCS0009 (cuello/cabeza)
                                      └─ UBEC 5 V ─ Orange Pi Zero 3
                                                     ├─ USB: cámara
                                                     ├─ UART o USB: adaptadores de bus #1 y #2
                                                     ├─ I2C: BNO055 + VL53L5CX
                                                     └─ GPIO: 4x SS-10 (punta/talón de cada pie)
```

- Un mazo de 3 cables por pierna (los servos se conectan en cadena).
- La Orange Pi Zero 3 tiene un solo puerto USB-A, que usa la cámara: los adaptadores de bus se
  conectan por UART del conector de 26 pines, o con un hub USB pequeño.

## Peso (según el modelo)

| Grupo | Masa |
|---|---|
| 12 STS3215 | 660 g |
| 4 SCS0009 | 48 g |
| Batería 2x18650 + soporte | 98 g |
| Orange Pi + reguladores + adaptadores + BMS + cableado | ~75 g |
| Sensores (IMU, ToF, cámara, pisada) | ~15 g |
| Plástico (torso, cabeza, piernas, pies con TPU) | ~200 g |
| **Total** | **~1.10 kg** |

Queda ~100 g por encima de la meta de 1 kg de la especificación. Los servos de las piernas son el
60 % del peso; se puede recortar algo con carcasas más finas o una batería más chica (a costa de
autonomía), pero con 12 STS3215 es difícil bajar de ~1.05 kg.

## Para verificar antes de comprar

- **Voltaje de los STS3215:** la batería cargada da 8.4 V y el rango indicado del servo es 6–7.4 V.
  Open Duck los alimenta directo de 2x18650; confirmarlo en la hoja de datos de Feetech (si no, un
  regulador de 7.4 V de alta corriente).
- **SCS0009:** confirmar precio y que el adaptador de bus y la biblioteca de Feetech manejan su
  protocolo (SCS), que es de la misma familia que el de los STS.
- **Orange Pi Zero 3:** confirmar en el esquemático oficial qué pines son UART e I2C (las fuentes no
  coinciden) y el consumo real.
- **BNO055:** algunas placas tienen problemas con su I2C; si pasa, usar su modo UART.
- **VL53L5CX/L8CX:** necesita cargar su firmware por I2C al arrancar (lo hace la biblioteca de ST).

## Fuentes

- STS3215: [Core Electronics](https://core-electronics.com.au/feetech-sts3215-smart-servo.html),
  [RobotShop](https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm)
- SCS0009: [OpenELAB](https://openelab.io/products/seeed-studio-feetech-scs0009-ultra),
  [Pakronics](https://www.pakronics.com.au/products/feetech-scs0009-ultra-compact-servo-6v-2-3kg-for-amazing-hand-ss100067882)
- Orange Pi Zero 3: [CNX Software](https://www.cnx-software.com/2023/07/03/orange-pi-zero-3-allwinner-h618-sbc)
- Lista de piezas de Open Duck Mini v2 (precios de referencia):
  [Google Sheets](https://docs.google.com/spreadsheets/d/1gq4iWWHEJVgAA_eemkTEsshXqrYlFxXAPwO515KpCJc)
