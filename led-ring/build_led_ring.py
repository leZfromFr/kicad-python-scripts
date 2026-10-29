"""24 WS2812B LEDs placed in a ring, data chain routed, GND vias, VDD/GND planes. Writes led_ring.kicad_pcb."""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ring_lib as R

board = pcbnew.CreateEmptyBoard()
leds = R.build_base(board, scattered=False)
for i in range(R.N - 1):
    R.data_track(board, leds, i)
for i in range(R.N):
    R.gnd_via(board, leds, i)
R.zones(board)
board = R.save_filled(board, "led_ring.kicad_pcb")
print("led_ring.kicad_pcb:", len(board.GetFootprints()), "LEDs")
