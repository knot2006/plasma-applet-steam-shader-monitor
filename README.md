# Steam Shader Monitor (KDE Plasma 6 Widget)

A lightweight KDE Plasma 6 widget that monitors background Steam Vulkan shader pre-caching and compilation (`fossilize_replay`).

![KDE Plasma 6](https://img.shields.io/badge/KDE%20Plasma-6.x-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Why this widget?

When Steam downloads Vulkan shader pre-caching archives, it processes and compiles the pipelines in the background across your CPU threads via `fossilize_replay`. Steam's GUI gives little to no visibility into this background work once downloads complete: the Downloads queue clears to 0 while your CPU quietly works on shaders.

**Steam Shader Monitor** bridges this gap by providing real-time visibility straight from your KDE panel.

---

## Features

- **Panel Indicator:**
  - **Idle:** Dimmed Steam icon when no shader jobs are running.
  - **Active:** Lights up with real-time percentage completion (e.g., `Steam 75%`).
- **Hover Tooltip:** Shows the currently compiling game title and pipeline counts.
- **Click Popup:** Expands an informative dashboard:
  - Game Name & Steam App ID
  - Live animated progress bar
  - Compiled vs. remaining pipeline counts
  - Active CPU thread count allocated to Fossilize
- **Lightweight & Fast:** Pure QML frontend calling a fast (~30ms) Python helper that parses Steam's local logs and process table without CPU overhead.

---

## Requirements

- **KDE Plasma 6** (`plasma5support` enabled, standard on Plasma 6)
- **Python 3**
- **Steam** (Native Linux client)

---

## Installation

### Method 1: Using `kpackagetool6`

```bash
git clone https://github.com/knot2006/plasma-applet-steam-shader-monitor.git
cd plasma-applet-steam-shader-monitor
kpackagetool6 -t Plasma/Applet -i .
```

To update in the future:
```bash
kpackagetool6 -t Plasma/Applet -u .
```

### Method 2: Manual Installation

Copy or symlink the folder into your local Plasma plasmoids directory:

```bash
mkdir -p ~/.local/share/plasma/plasmoids/
cp -r plasma-applet-steam-shader-monitor ~/.local/share/plasma/plasmoids/org.kde.plasma.steamshaders
```

Then restart or add the widget:
1. Right-click your KDE panel or desktop &rarr; **Add Widgets...**
2. Search for **Steam Shader Monitor**.
3. Drag and drop it onto your panel or system tray.

---

## Testing / Simulation

To test the widget UI and animations without waiting for an actual game update, you can run:

```bash
python3 -c '
import time, json, os

total = 42800
steps = [5, 15, 30, 48, 65, 80, 92, 100]

for pct in steps:
    with open("/tmp/steam_shader_mock.json", "w") as f:
        json.dump({
            "active": True,
            "game": "Overwatch 2",
            "app_id": "2357570",
            "percent": pct,
            "counts": f"{int(total * pct / 100)} / {total}",
            "threads": 12,
            "status": f"{pct}%"
        }, f)
    time.sleep(2)

time.sleep(2)
if os.path.exists("/tmp/steam_shader_mock.json"):
    os.remove("/tmp/steam_shader_mock.json")
'
```

---

## License

[MIT](LICENSE)
