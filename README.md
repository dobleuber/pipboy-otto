# Pip-Boy Octopus Edition

A Pip-Boy 3000 clone interface with **Otto** - a cybernetic octopus assistant!

![Otto the Pip-Boy](assets/otto_v1.png)

## Features

- 📊 **STATS** - System monitoring (CPU, RAM, disk, temperature)
- 💻 **SYSTEM** - System information and specs
- 🌐 **NETWORK** - Network status and interfaces
- 🐙 **OTTO** - The cybernetic octopus mascot
- 📋 **LOGS** - System event log
- ❓ **HELP** - Built-in help system

## Hardware / 3D Printed Body

The `cad/` directory contains OpenSCAD designs for **Otto's physical body** — a 3D printable enclosure that holds the actual hardware:

### Components
- **Orange Pi 5 Pro** — Brain (85×56×15mm)
- **5" display** — Otto's face (121×78mm)
- **2× SG90 servos** — Pan-tilt head mechanism
- **Arducam** — Otto's eyes (25×25mm)
- **Strap tabs** — Mount to backpack/strap

### Rendering

Requires [OpenSCAD](https://openscad.org/):

```bash
# Preview
openscad cad/otto-real-v0.2.scad -o preview.png

# Export STL for printing
openscad cad/otto-real-v0.2.scad -o otto-body.stl
```

## Requirements (Software)

- Python 3.8+
- Pygame 2.5+
- psutil

## Installation

```bash
git clone https://github.com/dobleuber/pipboy-otto.git
cd pipboy-octopus

# Install dependencies
pip install pygame psutil

# Run
SDL_VIDEODRIVER=wayland python3 pipboy.py
```

## Controls

| Key | Action |
|-----|------|
| TAB / → | Next section |
| ← | Previous section |
| 1-6 | Jump to section |
| H | Toggle help overlay |
| L | Add test log entry |
| ESC | Exit |

## Project Structure

```
pipboy-octopus/
├── pipboy.py          # Main application with UI
├── core.py            # Core logic (testable)
├── test_pipboy.py     # Unit tests
├── launch.sh          # Launcher script
├── cad/
│   └── otto-real-v0.2.scad  # 3D printable body (OpenSCAD)
├── assets/            # Images and media
└── README.md          # This file
```

## License

MIT
