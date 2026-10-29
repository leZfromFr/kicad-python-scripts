"""Length-matching demo: CLK (short, straight) gets a serpentine so it matches DATA (long detour)."""
import math
import os
import sys

import pcbnew
from pcbnew import Edge_Cuts, F_Cu, F_SilkS, FromMM, NETINFO_ITEM, PCB_ARC, PCB_SHAPE, PCB_TEXT, PCB_TRACK, ToMM, VECTOR2I

BOARD = (100.0, 92.0, 160.0, 126.0)       # x0, y0, x1, y1 (mm)
W = 0.3                                    # track width
R_MEANDER = 0.8                            # serpentine bend radius (leg pitch = 1.6 mm)
N_LEGS = 12
X_MID = 130.0
R_FILLET = 1.5
B_LOW = 120.0                              # DATA detour depth under U3


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


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def pad(fp, num):
    return [p for p in fp.Pads() if p.GetNumber() == num][0]


def pxy(p):
    q = p.GetPosition()
    return ToMM(q.x), ToMM(q.y)


def line(board, a, b, layer=Edge_Cuts, w=0.1):
    s = PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(mm(*a))
    s.SetEnd(mm(*b))
    s.SetLayer(layer)
    s.SetWidth(FromMM(w))
    board.Add(s)


def text(board, s, x, y, size=1.4):
    t = PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(mm(x, y))
    t.SetLayer(F_SilkS)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(size * 0.18))
    board.Add(t)


def footprint(board, lib, name, ref, x, y, rot=0):
    fp = pcbnew.FootprintLoad(os.path.join(kicad_footprint_dir(), lib + ".pretty"), name)
    fp.SetReference(ref)
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)
    fp.Value().SetVisible(False)
    board.Add(fp)
    return fp


def build_base(board):
    """Outline, chips, nets, labels and the DATA track. Returns (u1, u2)."""
    x0, y0, x1, y1 = BOARD
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        line(board, a, b)
    u1 = footprint(board, "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "U1", 108, 105)
    u2 = footprint(board, "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "U2", 152, 105)
    footprint(board, "Package_QFP", "LQFP-32_7x7mm_P0.8mm", "U3", X_MID, 110.5)
    clk, data = net(board, "CLK"), net(board, "DATA")
    pad(u1, "8").SetNet(clk)
    pad(u2, "1").SetNet(clk)
    pad(u1, "7").SetNet(data)
    pad(u2, "2").SetNet(data)
    text(board, "CLK", 112.5, 99.0)
    text(board, "DATA", 113.5, 123.0)
    for item in data_path(u1, u2):
        add(board, item, data)
    return u1, u2


# ---- geometry as plain tuples: ("L", a, b) or ("A", start, mid, end) ----

def rounded(points, r):
    """Polyline with 90-degree corners -> segments + fillet arcs."""
    out, cur = [], points[0]
    for i in range(1, len(points) - 1):
        p, q, n = points[i - 1], points[i], points[i + 1]
        u = ((q[0] - p[0]) / math.dist(p, q), (q[1] - p[1]) / math.dist(p, q))
        v = ((n[0] - q[0]) / math.dist(q, n), (n[1] - q[1]) / math.dist(q, n))
        t1 = (q[0] - u[0] * r, q[1] - u[1] * r)
        t2 = (q[0] + v[0] * r, q[1] + v[1] * r)
        c = (t1[0] + v[0] * r, t1[1] + v[1] * r)
        d = math.dist(c, q)
        mid = (c[0] + (q[0] - c[0]) / d * r, c[1] + (q[1] - c[1]) / d * r)
        out.append(("L", cur, t1))
        out.append(("A", t1, mid, t2))
        cur = t2
    out.append(("L", cur, points[-1]))
    return out


def data_path(u1, u2):
    (ax, ay), (bx, by) = pxy(pad(u1, "7")), pxy(pad(u2, "2"))
    return rounded([(ax, ay), (ax + 4, ay), (ax + 4, B_LOW), (bx - 4, B_LOW), (bx - 4, by), (bx, by)], R_FILLET)


def clk_path(u1, u2, h=None):
    """Straight CLK, or with a serpentine whose legs rise h mm above the track (h=None -> straight)."""
    (ax, y), (bx, _) = pxy(pad(u1, "8")), pxy(pad(u2, "1"))
    if h is None:
        return [("L", (ax, y), (bx, y))]
    r, n = R_MEANDER, N_LEGS
    xs = X_MID - r * n
    s2 = math.sqrt(0.5)
    xl = [xs + r + 2 * r * k for k in range(n)]
    lo, hi = y - r, y - h
    out = [("L", (ax, y), (xs, y)), ("A", (xs, y), (xs + s2 * r, y - r + s2 * r), (xl[0], lo))]
    for k in range(n):
        a, b = (lo, hi) if k % 2 == 0 else (hi, lo)
        if abs(a - b) > 1e-6:
            out.append(("L", (xl[k], a), (xl[k], b)))
        if k < n - 1:
            cx, cy = xl[k] + r, b
            out.append(("A", (xl[k], cy), (cx, cy - r if k % 2 == 0 else cy + r), (xl[k + 1], cy)))
    xe = xl[-1] + r
    out.append(("A", (xl[-1], lo), (xe - s2 * r, y - r + s2 * r), (xe, y)))
    out.append(("L", (xe, y), (bx, y)))
    return out


def length(path):
    total = 0.0
    for it in path:
        if it[0] == "L":
            total += math.dist(it[1], it[2])
        else:
            _, s, m, e = it
            # circumcircle radius + angle
            ax, ay = s; bx, by = m; cx, cy = e
            d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
            uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
            rr = math.dist((ux, uy), s)
            chord = math.dist(s, e)
            ang = 2 * math.asin(min(1, chord / (2 * rr)))
            # mid on the far side -> major arc never happens here (all arcs <= 180 deg)
            total += rr * ang
    return total


def h_for_match(u1, u2):
    target = length(data_path(u1, u2))
    lo, hi = R_MEANDER, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if length(clk_path(u1, u2, mid)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def add(board, it, netinfo, w=W):
    if it[0] == "L":
        t = PCB_TRACK(board)
        t.SetStart(mm(*it[1]))
        t.SetEnd(mm(*it[2]))
    else:
        t = PCB_ARC(board)
        t.SetStart(mm(*it[1]))
        t.SetMid(mm(*it[2]))
        t.SetEnd(mm(*it[3]))
    t.SetWidth(FromMM(w))
    t.SetLayer(F_Cu)
    t.SetNet(netinfo)
    board.Add(t)
    return t


def net_length(board, name):
    return sum(ToMM(t.GetLength()) for t in board.GetTracks() if t.GetNetname() == name)


def sample(path, step=0.1):
    """Dense polyline (for the race overlay)."""
    pts = []
    for it in path:
        if it[0] == "L":
            (x0, y0), (x1, y1) = it[1], it[2]
            n = max(1, int(math.dist(it[1], it[2]) / step))
            pts += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
        else:
            _, s, m, e = it
            ax, ay = s; bx, by = m; cx, cy = e
            d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
            uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
            rr = math.dist((ux, uy), s)
            a0, am, a1 = (math.atan2(p[1] - uy, p[0] - ux) for p in (s, m, e))
            def norm(a): return (a - a0) % (2 * math.pi)
            sweep = norm(a1) if norm(am) < norm(a1) else norm(a1) - 2 * math.pi
            n = max(2, int(abs(sweep) * rr / step))
            pts += [(ux + rr * math.cos(a0 + sweep * i / n), uy + rr * math.sin(a0 + sweep * i / n)) for i in range(n)]
    last = path[-1]
    pts.append(last[2] if last[0] == "L" else last[3])
    return [(round(x, 3), round(y, 3)) for x, y in pts]
