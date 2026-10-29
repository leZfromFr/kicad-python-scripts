# LED ring: 24 WS2812B in a perfect circle

![24 WS2812B LEDs placed in a ring by a KiCad Python script, with routed data chain and power planes](../images/led-ring.png)

Places 24 WS2812B LEDs on a circle with `sin`/`cos`, each one rotated to follow the ring, routes the DOUT→DIN data chain, adds a GND via per LED and pours VDD/GND planes.

Run it with the **Python bundled with KiCad**, from this folder:

```bash
# Windows
"C:\Program Files\KiCad\10.0\bin\python.exe" build_led_ring.py
# -> led_ring.kicad_pcb
```

The key part:

```python
for i, led in enumerate(leds):
    a = 2 * math.pi * i / 24
    x = cx + r * math.sin(a)
    y = cy - r * math.cos(a)        # KiCad's Y axis points down
    led.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    led.SetOrientationDegrees(90 - 15 * i)
```

- [Tutorial: circular footprint placement](https://scriptedpcb.com/en/pcbnew/circular-footprint-placement-api-python/)
- [Short: Never place LEDs in a circle by hand again](https://youtube.com/shorts/NsocVp2DxrI)

Back to [all KiCad Python scripts](../README.md) · Tutorials on [scriptedpcb.com](https://scriptedpcb.com/en/)
