"""
Reglas globales del motor de juego (fuente única de verdad).
================================================================
Constantes de gameplay compartidas por el motor (engine/) y la CPU.
Cualquier ajuste de balance debe hacerse aquí, no inline en los routers.
"""

# Mínimo de lanzamientos registrados del pitcher activo antes de que se
# permita (o la CPU considere) un cambio de pitcher.
MIN_PITCHES_TO_CHANGE = 5

# Entrada a partir de la cual las cartas tácticas de categoría EXTRA_INNINGS
# pueden activarse (las reglas de juego completo duran 9 entradas).
EXTRA_INNINGS_MIN_INNING = 10