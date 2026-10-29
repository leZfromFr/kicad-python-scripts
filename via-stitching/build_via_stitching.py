"""50 x 50 mm board, GND planes on both layers, 1,076 stitching vias that avoid the 4 mounting holes."""
import os
import sys
import time

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vias_lib import add_via, build_base, gnd, save_filled, via_points

board = pcbnew.CreateEmptyBoard()
build_base(board)
net = gnd(board)
t = time.perf_counter()
pts = via_points()
for x, y in pts:
    add_via(board, net, x, y)
print(f"{len(pts)} vias added in {time.perf_counter() - t:.2f} s")
board = save_filled(board, "via_stitching.kicad_pcb")
print("via_stitching.kicad_pcb written")
