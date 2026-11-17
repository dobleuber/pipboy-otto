// Cabeza fija del soporte del morral, con el tubo HORIZONTAL (solo para la prueba de diseño
// generativo: el pasador de la bisagra y el tubo quedan paralelos, a lo largo de Z).
// Marco de la pieza: X = x del usuario (adelante) desde el eje de la bisagra, Y = hacia abajo
// desde la cara de apoyo de la placa móvil, Z = y del usuario (hacia la izquierda) desde la cara
// exterior. Z hacia arriba es la cama de impresión hacia arriba.
include <../cad/mounts.scad>
PART = "none";
HEAD_AT = [-154, -225, -60];   // tubo horizontal (en el diseño: -45)
Y_MIN = ARM_BASE[1] - RX_W / 2;   // cara exterior (lado derecho)
echo(str("G:Y_MIN=", Y_MIN, " HINGE=", HINGE, " PLATE_Z=", PLATE_Z, " RX_ORIGIN=", RX_ORIGIN, " TUBE_LEN=", TUBE_LEN));
multmatrix([[1, 0, 0, -HINGE[0]], [0, 0, -1, PLATE_Z], [0, 1, 0, -Y_MIN], [0, 0, 0, 1]]) head_fixed();
