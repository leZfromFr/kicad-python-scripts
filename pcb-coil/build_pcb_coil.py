"""Build a 2-layer PCB coil from scratch with KiCad's pcbnew API.

Two 8-turn spirals (front and back, opposite spins), a centre via and a 2-pin connector.
Run with KiCad's bundled Python:  python build_pcb_coil.py [name] [--stages]
"""
import math
import os
import sys

import pcbnew
from pcbnew import (EDA_ANGLE, DEGREES_T, FOOTPRINT, F_Cu, B_Cu, Edge_Cuts, F_SilkS, FromMM,
                    NETINFO_ITEM, PAD, PCB_SHAPE, PCB_TEXT, PCB_TRACK, PCB_VIA, VECTOR2I)

OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "pcb_coil"
STAGES = "--stages" in sys.argv

CX, CY = 115.0, 105.0      # coil centre (mm)
RADIUS = 0.5               # start radius (mm)
SIDES = 20.0               # segments in the first turn (+4 per turn)
TRACK_W = 0.4              # track width (mm)
PITCH = 0.6                # distance between turns (mm)
TURNS = 8


def spiral(spin):
    """Points of the spiral, from the centre outwards (same maths as the original script)."""
    pts = []
    segs = SIDES
    for j in range(TURNS):
        segs += 4.0
        seg_angle = 360.0 / segs
        seg_radius = PITCH / segs
        for i in range(int(segs) + 1):
            if j > 0 and i == 0:
                continue  # first point of a turn = last point of the previous one
            r = RADIUS + seg_radius * i + PITCH * (j + 1)
            a = math.radians(seg_angle * spin * i)
            pts.append((CX + r * math.sin(a), CY + r * math.cos(a)))
    return pts


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def add_track(board, net, layer, a, b, width=TRACK_W):
    t = PCB_TRACK(board)
    t.SetStart(mm(*a))
    t.SetEnd(mm(*b))
    t.SetWidth(FromMM(width))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)


stage_no = 0


def save_stage(board, name):
    global stage_no
    if STAGES:
        stage_no += 1
        pcbnew.SaveBoard(f"{OUT}_stage{stage_no:02d}_{name}.kicad_pcb", board)


board = pcbnew.CreateEmptyBoard()

# 1. Board outline
outline = PCB_SHAPE(board)
outline.SetShape(pcbnew.SHAPE_T_RECT)
outline.SetStart(mm(CX - 10, CY - 9))
outline.SetEnd(mm(CX + 10, CY + 13))
outline.SetLayer(Edge_Cuts)
outline.SetWidth(FromMM(0.1))
board.Add(outline)
save_stage(board, "outline")

# 2. One net for the whole coil. It must end up on a pad, or pcbnew drops it on save.
net = NETINFO_ITEM(board, "COIL")
board.Add(net)

# 3. Front spiral, turn by turn
front = spiral(spin=-1)
points_per_turn = []
segs = SIDES
for _ in range(TURNS):
    segs += 4
    points_per_turn.append(int(segs))
idx = 0
for turn, n in enumerate(points_per_turn):
    for _ in range(n):
        add_track(board, net, F_Cu, front[idx], front[idx + 1])
        idx += 1
    save_stage(board, f"front_turn{turn + 1}")

# 4. Via at the centre, linking both layers
via = PCB_VIA(board)
via.SetPosition(mm(*front[0]))
try:
    via.SetWidth(via.TopLayer(), FromMM(0.6))   # KiCad 9/10
except TypeError:
    via.SetWidth(FromMM(0.6))                   # KiCad 8
via.SetDrill(FromMM(0.3))
via.SetNet(net)
board.Add(via)
save_stage(board, "via")

# 5. Back spiral, opposite spin so the current keeps turning the same way
back = spiral(spin=+1)
idx = 0
for turn, n in enumerate(points_per_turn):
    for _ in range(n):
        add_track(board, net, B_Cu, back[idx], back[idx + 1])
        idx += 1
    save_stage(board, f"back_turn{turn + 1}")

# 6. Two-pin connector, one lead-out per layer
fp = FOOTPRINT(board)
fp.SetReference("J1")
fp.SetValue("COIL")
fp.SetPosition(mm(CX, CY + 9.5))
for number, dx in (("1", -1.27), ("2", 1.27)):
    pad = PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT if number == "1" else pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(mm(1.7, 1.7))
    pad.SetDrillSize(mm(1.0, 1.0))
    pad.SetLayerSet(PAD.PTHMask())
    pad.SetPosition(mm(CX + dx, CY + 9.5))
    pad.SetNet(net)
    fp.Add(pad)
fp.Reference().SetPosition(mm(CX, CY + 11.6))
fp.Reference().SetTextSize(mm(0.8, 0.8))
fp.Value().SetVisible(False)
board.Add(fp)
add_track(board, net, F_Cu, front[-1], (CX - 1.27, CY + 9.5))
add_track(board, net, B_Cu, back[-1], (CX + 1.27, CY + 9.5))

label = PCB_TEXT(board)
label.SetText("PCB COIL")
label.SetPosition(mm(CX, CY - 7.5))
label.SetLayer(F_SilkS)
label.SetTextSize(mm(1.2, 1.2))
board.Add(label)
save_stage(board, "connector")

pcbnew.SaveBoard(f"{OUT}.kicad_pcb", board)
tracks = [t for t in board.GetTracks() if not isinstance(t, PCB_VIA)]
print(f"saved {OUT}.kicad_pcb: {len(tracks)} track segments, "
      f"{len(board.GetTracks()) - len(tracks)} via, {len(board.GetFootprints())} footprint")
