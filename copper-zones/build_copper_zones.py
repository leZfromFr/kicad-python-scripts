"""Six copper zones of different shapes (circle, rounded rectangle, hexagon, star, ring, arrow) + a hatched GND plane."""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zones_lib import build_steps, save_filled

board = pcbnew.CreateEmptyBoard()
for step in build_steps(board):
    step()
board = save_filled(board, "copper_zones.kicad_pcb")
print("copper_zones.kicad_pcb:", len(board.Zones()), "zones")
