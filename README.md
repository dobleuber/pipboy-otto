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

## Requirements

- Python 3.8+
- Pygame 2.5+
- psutil

## Installation

```bash
# Clone el repositorio
git clone https://github.com/dobleuber/pipboy-otto.git

# Or download manually
wget https://github.com/dobleuber/pipboy-otto/archive/main.zip
unzip pipboy-octopus.zip

# Install dependencies
pip install pygame psutil

# Or on Ubuntu/Debian-based systems:
sudo apt install python3-pygame python3-psutil

# Run
cd pipboy-octopus
SDL_VIDEODRIVER=wayland python3 pipboy.py
```

```

## Controls

| Key | Action |
|-----|------|
| TAB / → | Next section |
| ← | → | Previous section |
    H | Toggle help overlay |
    ESC | Exit |
    1-6 | Jump to section (1-6) |
    L | Add test log entry |
    ARROWS | Navigate sections |
    H | Toggle help |

## Project Structure

```
pipboy-octopus/
├── pipboy.py          # Main application with UI
├── core.py              # Core logic (testable)
├── test_pipboy.py        # Unit tests
├── README.md            # This file
├── .gitignore            # Git ignore file
├── launch.sh              # Launcher script
```

## License

MIT
