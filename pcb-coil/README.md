# PCB coil: 16 turns on 2 layers

![Two-layer spiral PCB coil generated with KiCad's Python API](../images/pcb-coil.png)

Two 8-turn spirals (front and back) joined by a centre via and brought out to a 2-pin connector. The back spiral winds the opposite way so the current keeps turning in the same direction on both layers. Add `--stages` to save one board per step.

Run it with the **Python bundled with KiCad**, from this folder:

```bash
# Windows
"C:\Program Files\KiCad\10.0\bin\python.exe" build_pcb_coil.py
# -> pcb_coil.kicad_pcb
```

The key part:

```python
front, back = spiral(spin=-1), spiral(spin=+1)   # opposite spins: the fields add up
```

- [Video: I Asked an AI to Design a PCB… and Watched It Draw Itself in KiCad](https://youtu.be/9d822YdP7yQ)
- [Short: AI builds a PCB live in KiCad](https://youtube.com/shorts/V0x1Cqmirws)

Back to [all KiCad Python scripts](../README.md) · Tutorials on [scriptedpcb.com](https://scriptedpcb.com/en/)
