#!/bin/sh
# Exporta todas las piezas de la pierna (izquierda y derecha) a stl/.
cd "$(dirname "$0")"
mkdir -p stl
for p in yaw_link roll_link thigh shin ankle_cross foot sole; do
  openscad -q --export-format binstl -o stl/left_$p.stl -D "PART=\"$p\"" leg.scad
  openscad -q --export-format binstl -o stl/right_$p.stl -D "PART=\"$p\"" -D 'MIRROR=true' leg.scad
  cp stl/left_$p.stl stl/$p.stl
done
openscad -q --export-format binstl -o stl/servo.stl -D 'PART="servo"' leg.scad
openscad -q --export-format binstl -o stl/servo_check.stl -D 'PART="servo_check"' -D 'SERVO_INSET=0.3' leg.scad
