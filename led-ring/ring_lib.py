"""24x WS2812B LED ring, placed and routed with pcbnew."""
import math
import os
import random
import sys

import pcbnew
from pcbnew import B_Cu, Edge_Cuts, F_Cu, FromMM, NETINFO_ITEM, PCB_SHAPE, PCB_TRACK, PCB_VIA, SHAPE_LINE_CHAIN, VECTOR2I, ZONE

CX, CY = 115.0, 105.0
N = 24
R_LED = 29.5
R_OUT, R_IN = 35.0, 23.0
FP_NAME = "LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm"
TRACK_W = 0.3


def kicad_footprint_dir():
    """KiCad's stock footprint libraries, found from the running KiCad Python (Windows/macOS/Linux)."""
    for var in ("KICAD10_FOOTPRINT_DIR", "KICAD9_FOOTPRINT_DIR", "KICAD8_FOOTPRINT_DIR"):
        if os.environ.get(var):
            return os.environ[var]
    exe = os.path.dirname(os.path.realpath(sys.executable))
    for cand in (os.path.join(exe, "..", "share", "kicad", "footprints"),               # Windows
                 os.path.join(exe, "..", "..", "..", "..", "..", "SharedSupport", "footprints"),  # macOS
                 "/usr/share/kicad/footprints", "/usr/local/share/kicad/footprints"):   # Linux
        if os.path.isdir(cand):
            return os.path.normpath(cand)
    raise SystemExit("KiCad footprint libraries not found: set KICAD10_FOOTPRINT_DIR")


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def set_via_size(via, diameter_mm):
    """KiCad 9/10 take (layer, width); KiCad 8 takes only (width)."""
    try:
        via.SetWidth(via.TopLayer(), FromMM(diameter_mm))
    except TypeError:
        via.SetWidth(FromMM(diameter_mm))


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def target(i):
    """Ring position and orientation of LED i: local +x points outwards, +y along the ring."""
    th = 2 * math.pi * i / N
    return CX + R_LED * math.sin(th), CY - R_LED * math.cos(th), 90 - 360 * i / N


def chaos(i, seed=7):
    rnd = random.Random(seed * 100 + i)
    a = rnd.uniform(0, 2 * math.pi)
    r = rnd.uniform(0, 30)
    return CX + r * math.cos(a), CY + r * math.sin(a), rnd.uniform(-180, 180)


def circle(board, r):
    s = PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(mm(CX, CY))
    s.SetEnd(mm(CX + r, CY))
    s.SetLayer(Edge_Cuts)
    s.SetWidth(FromMM(0.1))
    board.Add(s)


def build_base(board, scattered=True):
    """Outline + 24 LEDs with their nets (VDD, GND, data chain D0..D24)."""
    circle(board, R_OUT)
    circle(board, R_IN)
    vdd, gnd = net(board, "VDD"), net(board, "GND")
    leds = []
    for i in range(N):
        fp = pcbnew.FootprintLoad(os.path.join(kicad_footprint_dir(), "LED_SMD.pretty"), FP_NAME)
        fp.SetReference(f"D{i + 1}")
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        x, y, rot = chaos(i) if scattered else target(i)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        for p in fp.Pads():
            n = p.GetNumber()
            if n == "1":
                p.SetNet(vdd)
            elif n == "3":
                p.SetNet(gnd)
            elif n == "4":          # DIN  <- previous LED
                p.SetNet(net(board, f"D{i}"))
            elif n == "2":          # DOUT -> next LED
                p.SetNet(net(board, f"D{i + 1}"))
        board.Add(fp)
        leds.append(fp)
    return leds


def leds_of(board):
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    return [fps[f"D{i + 1}"] for i in range(N)]


def pad(fp, num):
    return [p for p in fp.Pads() if p.GetNumber() == num][0]


def move(fp, x, y, rot):
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)


def track(board, a, b, netinfo, layer=F_Cu, w=TRACK_W):
    t = PCB_TRACK(board)
    t.SetStart(a)
    t.SetEnd(b)
    t.SetWidth(FromMM(w))
    t.SetLayer(layer)
    t.SetNet(netinfo)
    board.Add(t)
    return t


def data_track(board, leds, i):
    """DOUT of LED i -> DIN of LED i+1."""
    a, b = pad(leds[i], "2"), pad(leds[i + 1], "4")
    return [track(board, a.GetPosition(), b.GetPosition(), a.GetNet())]


def gnd_via(board, leds, i):
    """GND pad -> via just outside it -> GND plane on B.Cu."""
    fp = leds[i]
    p = pad(fp, "3")
    th = 2 * math.pi * i / N
    pp = p.GetPosition()
    vx = pcbnew.ToMM(pp.x) + 1.5 * math.sin(th)
    vy = pcbnew.ToMM(pp.y) - 1.5 * math.cos(th)
    v = PCB_VIA(board)
    v.SetPosition(mm(vx, vy))
    set_via_size(v, 0.6)
    v.SetDrill(FromMM(0.3))
    v.SetNet(p.GetNet())
    board.Add(v)
    return [v, track(board, pp, mm(vx, vy), p.GetNet(), w=0.4)]


def ring_zone(board, layer, netname, r_out, r_in):
    z = ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(board, netname))
    for r, hole in ((r_out, False), (r_in, True)):
        c = SHAPE_LINE_CHAIN()
        for k in range(96):
            a = 2 * math.pi * k / 96
            c.Append(FromMM(CX + r * math.cos(a)), FromMM(CY + r * math.sin(a)))
        c.SetClosed(True)
        if hole:
            z.Outline().AddHole(c)
        else:
            z.Outline().AddOutline(c)
    z.SetLocalClearance(FromMM(0.3))
    board.Add(z)
    return z


def zones(board):
    return [ring_zone(board, F_Cu, "VDD", R_OUT - 0.5, R_IN + 0.5), ring_zone(board, B_Cu, "GND", R_OUT - 0.5, R_IN + 0.5)]


def save_filled(board, path):
    """Fill every zone and save. The board is saved and reloaded first: on KiCad 9, filling a board
    built in memory with CreateEmptyBoard() crashes (access violation), a reloaded one fills fine."""
    pcbnew.SaveBoard(path, board)
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    return board
