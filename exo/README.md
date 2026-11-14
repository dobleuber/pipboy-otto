# Exoesqueleto Otto — diseño conceptual v0.1

Exoesqueleto modular de piernas para caminar y correr: seis motores en módulos de
cadera, rodilla y tobillo que se montan según la actividad. Esta carpeta contiene
el simulador de dimensionado, los datos de marcha y carrera, y la página
interactiva con el diseño completo.

El documento de diseño es la página: abre `viewer/index.html` en un navegador.

## Diseño en una tabla

| Eje | Motor | Par pico | Notas |
|---|---|---|---|
| Cadera, flexión/extensión | RobStride 04, directo | 120 N·m | Abducción y rotación pasivas |
| Rodilla, flexión/extensión | RobStride 04, directo | 120 N·m | Módulo desmontable |
| Tobillo, flexión plantar | CubeMars AK10-9 V3 + cuerda 2,5 : 1 | 132 N·m | Solo empuja; motor en la tibia |

| Configuración | Masa | Uso |
|---|---|---|
| Completo | 16,1 kg | Caminar, escaleras, carga |
| Cadera + tobillo | 10,8 kg | Trotar y correr hasta 3,5 m/s |
| Solo cadera | 7,6 kg | Primeras pruebas |
| Solo tobillo | 5,9 kg | Primeras pruebas |

## Qué hace el simulador

Dinámica inversa sobre movimiento humano medido. Los ángulos, momentos
articulares y fuerzas del suelo vienen de datos públicos; el exoesqueleto se
añade como masa y como fuentes de par, y cada motor se compara con su límite de
par, velocidad y temperatura. También estima consumo de batería, autonomía y
balance metabólico.

No es una simulación predictiva: asume que la persona se mueve igual con y sin el
equipo. El balance metabólico usa el *augmentation factor* de Mooney, Rouse y
Herr (2014), validado para caminar; en carrera es una extrapolación.

Parámetros supuestos, a medir en banco: constante de motor, fricción e inercia
de rotor de los RobStride (marcados `assumed` en `sim/exosim.js`). Las masas de
estructura son objetivos de diseño.

## Uso

```bash
node sim/cli.js                      # tabla de dimensionado, todas las configuraciones
node sim/cli.js --mass 85 --assist 0.4 --payload 10
node sim/sweep.js --assist 0.3       # selección de motores por eje
node --test sim/exosim.test.js       # pruebas
node viewer/build.js                 # regenera viewer/index.html
```

Para regenerar las curvas normativas desde los datos originales (unos 60 MB):

```bash
pip install numpy
python3 sim/fetch_data.py            # descarga a exo/raw (ignorado por git)
python3 sim/build_norm.py              # escribe data/gait_norm.json
```

## Archivos

```
exo/
├── data/gait_norm.json    # curvas medias de marcha y carrera (derivado)
├── sim/exosim.js          # simulador (Node y navegador)
├── sim/cli.js, sweep.js   # tablas de dimensionado y selección de motores
├── sim/exosim.test.js     # pruebas
├── sim/fetch_data.py      # descarga de datos públicos
├── sim/build_norm.py      # construcción de curvas normativas
└── viewer/                # template.html + build.js -> index.html
```

## Datos

- Marcha: Fukuchi, Fukuchi y Duarte (2018), PeerJ 6:e4640, doi:10.7717/peerj.4640.
  Caminadora a velocidad cómoda, 24 adultos jóvenes.
- Carrera: Fukuchi, Fukuchi y Duarte (2017), PeerJ 5:e3298, doi:10.7717/peerj.3298.
  Caminadora a 2,5, 3,5 y 4,5 m/s, de 31 a 39 corredores.

Ambos con licencia CC BY 4.0. `data/gait_norm.json` es un derivado de esos datos.

## Limitaciones conocidas

- Solo plano sagital. La velocidad reconstruida coincide con la medida al caminar
  (1,26 frente a 1,25 m/s) y queda entre 8 y 16 % corta al correr, porque el
  modelo no incluye la rotación de la pelvis.
- La inclinación de pelvis en carrera no está en los datos; se calibra exigiendo
  un vuelo balístico (resulta en 16–17°).
- El peso añadido aumenta los momentos articulares en proporción durante el apoyo.
