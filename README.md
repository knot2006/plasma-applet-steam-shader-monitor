<div align="center">
  <img src="logo.png" alt="Steam Shader Monitor Logo" width="140" />
  <h1>Steam Shader Monitor</h1>
  <p><strong>A lightweight KDE Plasma 6 widget monitoring background Steam Vulkan shader compilation.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/KDE%20Plasma-6.x-blue.svg" alt="KDE Plasma 6" />
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  </p>
</div>

---

## Overview

When Steam downloads Vulkan shader pre-caching packages, it processes and compiles the pipelines in the background across your CPU threads using `fossilize_replay`. Steam's GUI gives little to no visibility into this work once network downloads finish: the Downloads queue clears to 0 while your CPU is heavily compiling.

**Steam Shader Monitor** brings full visibility right to your KDE panel, status tray, or desktop.

<div align="center">
  <p><strong>Panel & Taskbar Integration (Live Active State)</strong></p>
>
  <img src="screenshot-active.png" alt="Steam Shader Monitor - Active Compilation" width="48%" />
  <img src="screenshot-idle.png" alt="Steam Shader Monitor - Idle" width="48%" />
</div>

---

## Features

- **Panel & System Tray Indicator:**
  - **Idle:** Dimmed Steam icon when no shader compilation is running.
  - **Active:** Lights up with live percentage completion (e.g., `Steam 74%`).
- **Hover Tooltip:** Shows the currently compiling game title and pipeline counts at a glance.
- **Click Popup Dashboard:**
  - Real game title (e.g., *Overwatch 2*, *HELLDIVERS™ 2*) & Steam App ID
  - Smooth animated progress bar
  - Compiled vs. total pipeline counts
  - Active CPU thread count allocated to Fossilize
- **Lightweight & Efficient:** Pure QML frontend calling a fast (~30ms) Python helper that inspects Steam's local logs and process table without CPU overhead.

Completion is calculated from the completed/total replay counts when available, because Steam's logged percentage can disagree with them. It uses whole percentages rounded down and falls back to Steam's percentage when counts are unavailable. Steam can revise the total during replay, so the percentage is not an estimate of time remaining.

---

## Requirements

- **KDE Plasma 6**
- **Python 3**
- **Steam** (Native Linux client)

---

## Installation

### Method 1: Using `kpackagetool6` (Recommended)

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

Copy into your local Plasma plasmoids directory:

```bash
mkdir -p ~/.local/share/plasma/plasmoids/
cp -r plasma-applet-steam-shader-monitor ~/.local/share/plasma/plasmoids/org.kde.plasma.steamshaders
```

Then add the widget:
1. Right-click your KDE panel or desktop &rarr; **Add Widgets...** (or enter Edit Mode).
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

## Releases

The GitHub Actions release workflow tests the shader helper, builds an installable `.plasmoid` package, and publishes it as a GitHub release whenever a `v*` tag is pushed. The tag must match `KPlugin.Version` in `metadata.json`. The workflow uses GitHub's built-in token; no additional secrets are required.

For example, after setting the version to `1.2` and committing the release changes:

```bash
git push origin main
git tag v1.2
git push origin v1.2
```

Download `org.kde.plasma.steamshaders.plasmoid` from the resulting [GitHub release](https://github.com/knot2006/plasma-applet-steam-shader-monitor/releases), then upload it to the Files section of the existing [KDE Store listing](https://store.kde.org/p/2379614) and set its version to match.

KDE Store publishing remains manual: automatic uploads are not currently supported, according to [OpenDesktop maintainers](https://forum.opendesktop.org/t/openhv/21070), and an official CI/CD publishing interface is still being [requested on KDE Discuss](https://discuss.kde.org/t/proposal-official-ci-cd-publishing-workflow-for-kde-store-opendesktop/50377). A GitHub release does not automatically update the Store listing.

The release workflow runs the helper tests. Run the full suite locally for the headless KDE QML checks, which need PyQt6 and KDE modules.

## Development checks

Run the regression tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The helper tests use temporary Steam installations and simulated process output. The headless UI tests require PyQt6 and the KDE QML modules; they are skipped when PyQt6 is unavailable. They cover command quoting, compact panel sizing, and loading the active and idle popup views.

To check the complete QML file:

```bash
qmllint contents/ui/main.qml
```

## License

[MIT](LICENSE) © Knot
