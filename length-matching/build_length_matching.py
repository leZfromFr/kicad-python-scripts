"""CLK takes a short path, DATA a long detour: a serpentine is grown on CLK until both have the same length."""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meander_lib as M

board = pcbnew.CreateEmptyBoard()
u1, u2 = M.build_base(board)
before = M.length(M.clk_path(u1, u2, None))
h = M.h_for_match(u1, u2)                       # bisection on the loop height
clk = M.net(board, "CLK")
for item in M.clk_path(u1, u2, h):              # segments + PCB_ARC bends
    M.add(board, item, clk)
pcbnew.SaveBoard("length_matching.kicad_pcb", board)
print(f"CLK {before:.3f} mm -> {M.net_length(board, 'CLK'):.3f} mm, DATA {M.net_length(board, 'DATA'):.3f} mm, loop height {h:.4f} mm")
