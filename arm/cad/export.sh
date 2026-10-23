#!/bin/sh
# Exporta cada pieza a stl/ (STL binario) y la placa de la espalda a DXF.
set -e
cd "$(dirname "$0")"
mkdir -p stl
for p in bandeja barra receptor mordaza perilla base_mesa pie_mastil cabeza_fija cabeza_movil caja tapa \
         probeta_riel probeta_receptor; do
  openscad -q --export-format binstl -D "PART=\"$p\"" -o "stl/$p.stl" mounts.scad
  echo "stl/$p.stl"
done
openscad -q -D 'PART="placa_espalda"' -o placa_espalda.dxf mounts.scad && echo placa_espalda.dxf
