"""Copper zones of many shapes, drawn with KiCad's pcbnew API.

build_steps(board) returns a list of callables; each one adds one element.
Used headless by build_copper_zones.py; the steps can also be run one by one in the scripting console.
"""
import math

import pcbnew
from pcbnew import (B_Cu, Edge_Cuts, F_Cu, F_Mask, F_SilkS, FOOTPRINT, FromMM, NETINFO_ITEM, PAD,
                    PCB_SHAPE, PCB_TEXT, PCB_VIA, SHAPE_LINE_CHAIN, SHAPE_POLY_SET, VECTOR2I, ZONE)

CX, CY = 115.0, 105.0
W, H = 56.0, 40.0
COLS = (CX - 14, CX, CX + 14)
ROWS = (CY - 7, CY + 8)


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def set_via_size(via, diameter_mm):
    """KiCad 9/10 take (layer, width); KiCad 8 takes only (width)."""
    try:
        via.SetWidth(via.TopLayer(), FromMM(diameter_mm))
    except TypeError:
        via.SetWidth(FromMM(diameter_mm))


def chain(points):
    c = SHAPE_LINE_CHAIN()
    for x, y in points:
        c.Append(FromMM(x), FromMM(y))
    c.SetClosed(True)
    return c


def poly(outline, holes=(), p=None):
    p = SHAPE_POLY_SET() if p is None else p
    p.AddOutline(chain(outline))
    for h in holes:
        p.AddHole(chain(h))
    return p


# ---- shapes (lists of (x, y) in mm) ----
def circle(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def regular(cx, cy, r, sides, start=-90):
    return [(cx + r * math.cos(math.radians(start + 360 * i / sides)),
             cy + r * math.sin(math.radians(start + 360 * i / sides))) for i in range(sides)]


def star(cx, cy, r_out, r_in, branches=5):
    pts = []
    for i in range(2 * branches):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(-90 + 180 * i / branches)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rounded_rect(cx, cy, w, h, r, n=8):
    pts = []
    corners = ((cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90),
               (cx - w / 2 + r, cy - h / 2 + r, 180), (cx + w / 2 - r, cy - h / 2 + r, 270))
    for ox, oy, a0 in corners:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def arrow(cx, cy, s):
    pts = [(-1, -0.35), (0.15, -0.35), (0.15, -0.8), (1, 0), (0.15, 0.8), (0.15, 0.35), (-1, 0.35)]
    return [(cx + s * x, cy + s * y) for x, y in pts]


SHAPES = [
    ("CIRCLE", lambda x, y: (circle(x, y, 5), []), (0, 0)),
    ("ROUNDED", lambda x, y: (rounded_rect(x, y, 10, 8.5, 2), []), (0, 0)),
    ("HEXAGON", lambda x, y: (regular(x, y, 5.2, 6, start=0), []), (0, 0)),
    ("STAR", lambda x, y: (star(x, y, 5.8, 2.4), []), (0, 0)),
    ("RING", lambda x, y: (circle(x, y, 5), [circle(x, y, 3)]), (0, 4)),
    ("ARROW", lambda x, y: (arrow(x, y, 5.5), []), (-2, 0)),
]


def build_steps(board):
    net = board.FindNet("GND")
    if net is None:
        net = NETINFO_ITEM(board, "GND")
        board.Add(net)
    state = {"net": net}

    def outline():
        s = PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_RECT)
        s.SetStart(mm(CX - W / 2, CY - H / 2))
        s.SetEnd(mm(CX + W / 2, CY + H / 2))
        s.SetLayer(Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)

    def mounting_holes():
        # A new net must sit on a pad, or pcbnew drops it on save: 4 GND mounting holes.
        for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
            x, y = CX + dx * (W / 2 - 4), CY + dy * (H / 2 - 4)
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
            pad.SetNet(state["net"])
            fp.Add(pad)
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)
            board.Add(fp)

    def shape_step(i):
        name, make, via_off = SHAPES[i]
        x, y = COLS[i % 3], ROWS[i // 3]

        out, holes = make(x, y)

        def add_zone():
            z = ZONE(board)
            z.SetLayer(F_Cu)
            z.SetNet(state["net"])
            poly(out, holes, z.Outline())   # fill the zone's own outline (SetOutline keeps a dangling pointer)
            z.SetZoneName(name)
            board.Add(z)

        def finish():
            mask = PCB_SHAPE(board)          # opening in the solder mask: gold copper in 3D
            mask.SetShape(pcbnew.SHAPE_T_POLY)
            mask.SetPolyShape(poly(out, holes))
            mask.SetFilled(True)
            mask.SetWidth(0)
            mask.SetLayer(F_Mask)
            board.Add(mask)
            via = PCB_VIA(board)             # stitching via down to the ground plane
            via.SetPosition(mm(x + via_off[0], y + via_off[1]))
            set_via_size(via, 0.8)
            via.SetDrill(FromMM(0.4))
            via.SetNet(state["net"])
            board.Add(via)
            t = PCB_TEXT(board)
            t.SetText(name)
            t.SetLayer(F_SilkS)
            t.SetTextSize(mm(1.1, 1.1))
            t.SetTextThickness(FromMM(0.18))
            t.SetPosition(mm(x, y + 6.9))
            board.Add(t)
        return [add_zone, finish]

    def ground_plane():
        z = ZONE(board)
        z.SetLayer(B_Cu)
        z.SetNet(state["net"])
        m = 0.5
        poly([(CX - W / 2 + m, CY - H / 2 + m), (CX + W / 2 - m, CY - H / 2 + m),
              (CX + W / 2 - m, CY + H / 2 - m), (CX - W / 2 + m, CY + H / 2 - m)], p=z.Outline())
        z.SetFillMode(pcbnew.ZONE_FILL_MODE_HATCH_PATTERN)
        z.SetHatchThickness(FromMM(0.6))
        z.SetHatchGap(FromMM(1.0))
        z.SetZoneName("GND_PLANE")
        board.Add(z)

    def title():
        t = PCB_TEXT(board)
        t.SetText("ZONES · pcbnew")
        t.SetLayer(F_SilkS)
        t.SetTextSize(mm(1.6, 1.6))
        t.SetTextThickness(FromMM(0.25))
        t.SetPosition(mm(CX, CY - H / 2 + 2.6))
        board.Add(t)

    shapes = [f for i in range(len(SHAPES)) for f in shape_step(i)]
    return [outline, mounting_holes] + shapes + [ground_plane, title]


def save_filled(board, path):
    """Fill every zone and save. The board is saved and reloaded first: on KiCad 9, filling a board
    built in memory with CreateEmptyBoard() crashes (access violation), a reloaded one fills fine."""
    pcbnew.SaveBoard(path, board)
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    return board
