# Copper zones of any shape

![Copper zones shaped as circle, rounded rectangle, hexagon, star, ring and arrow, drawn by a KiCad Python script](../images/copper-zones.png)

Six GND copper zones (circle, rounded rectangle, hexagon, star, ring with a hole, arrow) plus a hatched GND plane on the back. Every shape is just a list of points.

Run it with the **Python bundled with KiCad**, from this folder:

```bash
# Windows
"C:\Program Files\KiCad\10.0\bin\python.exe" build_copper_zones.py
# -> copper_zones.kicad_pcb
```

The key part:

```python
def star(cx, cy, r_out, r_in, branches=5):
    pts = []
    for i in range(2 * branches):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(-90 + 180 * i / branches)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

zone.Outline().AddOutline(chain(star(x, y, 5.8, 2.4)))   # not SetOutline(temporary_poly): it can crash
```

- [Tutorial: creating a copper zone](https://scriptedpcb.com/en/pcbnew/creating-copper-zone-api-python/)
- [Video: Stop Drawing KiCad Zones by Hand](https://youtu.be/w22P43g24Uk)
- [Short: KiCad copper zones drawn by code](https://youtube.com/shorts/IJrjht3GG3o)

Back to [all KiCad Python scripts](../README.md) · Tutorials on [scriptedpcb.com](https://scriptedpcb.com/en/)
