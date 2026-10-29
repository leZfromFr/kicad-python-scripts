"""Via stitching: 1000+ GND vias on a 2-layer board, with pcbnew."""
import math

import pcbnew
from pcbnew import (B_Cu, Edge_Cuts, F_Cu, F_SilkS, FOOTPRINT, FromMM, NETINFO_ITEM, PAD, PCB_SHAPE,
                    PCB_TEXT, PCB_VIA, SHAPE_LINE_CHAIN, VECTOR2I, ZONE)

CX, CY = 115.0, 105.0
SIZE = 50.0
PITCH = 1.4
HOLE_INSET = 4.0


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def set_via_size(via, diameter_mm):
    """KiCad 9/10 take (layer, width); KiCad 8 takes only (width)."""
    try:
        via.SetWidth(via.TopLayer(), FromMM(diameter_mm))
    except TypeError:
        via.SetWidth(FromMM(diameter_mm))


def holes():
    d = SIZE / 2 - HOLE_INSET
    return [(CX + sx * d, CY + sy * d) for sx in (-1, 1) for sy in (-1, 1)]


def gnd(board):
    net = board.FindNet("GND")
    if net is None:
        net = NETINFO_ITEM(board, "GND")
        board.Add(net)
    return net


def via_points():
    """Grid points sorted from the centre outwards (the 'wave')."""
    n = int((SIZE - 2 * 1.6) / PITCH)
    start = -n * PITCH / 2
    pts = []
    for i in range(n + 1):
        for j in range(n + 1):
            x, y = CX + start + i * PITCH, CY + start + j * PITCH
            if all(math.hypot(x - hx, y - hy) > 3.7 for hx, hy in holes()):
                pts.append((x, y))
    pts.sort(key=lambda p: (round(math.hypot(p[0] - CX, p[1] - CY), 3), math.atan2(p[1] - CY, p[0] - CX)))
    return pts


def build_base(board):
    """Outline, 4 GND mounting holes, GND planes on both layers."""
    net = gnd(board)
    s = PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(mm(CX - SIZE / 2, CY - SIZE / 2))
    s.SetEnd(mm(CX + SIZE / 2, CY + SIZE / 2))
    s.SetLayer(Edge_Cuts)
    s.SetWidth(FromMM(0.1))
    board.Add(s)
    for k, (x, y) in enumerate(holes()):
        fp = FOOTPRINT(board)
        fp.SetReference(f"H{k + 1}")
        fp.SetPosition(mm(x, y))
        pad = PAD(fp)
        pad.SetNumber("1")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(mm(5.0, 5.0))
        pad.SetDrillSize(mm(3.2, 3.2))
        pad.SetLayerSet(PAD.PTHMask())
        pad.SetPosition(mm(x, y))
        pad.SetNet(net)
        fp.Add(pad)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
    m = 0.5
    for layer in (F_Cu, B_Cu):
        z = ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net)
        c = SHAPE_LINE_CHAIN()
        for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            c.Append(FromMM(CX + x * (SIZE / 2 - m)), FromMM(CY + y * (SIZE / 2 - m)))
        c.SetClosed(True)
        z.Outline().AddOutline(c)
        board.Add(z)


def add_via(board, net, x, y):
    v = PCB_VIA(board)
    v.SetPosition(mm(x, y))
    set_via_size(v, 0.6)
    v.SetDrill(FromMM(0.3))
    v.SetNet(net)
    board.Add(v)
    return v


def save_filled(board, path):
    """Fill every zone and save. The board is saved and reloaded first: on KiCad 9, filling a board
    built in memory with CreateEmptyBoard() crashes (access violation), a reloaded one fills fine."""
    pcbnew.SaveBoard(path, board)
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    return board
