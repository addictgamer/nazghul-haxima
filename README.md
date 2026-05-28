# Nazghul / Haxima

Nazghul is a classic, party-based fantasy RPG engine and Haxima is its flagship game world.
This repository contains both:

- The original C/SDL engine and content.
- An actively developed Python/Pygame port in `pygame_haxima/`.

If you are new to this repository, start with the Pygame port.

## Pygame Port (Recommended)

The modern implementation lives in `pygame_haxima/` and is the easiest way to run and iterate on the game.

### Requirements

- Python 3.11+
- `pygame-ce`

Install dependencies:

```bash
cd pygame_haxima
pip install -e .
```

Optional development dependencies:

```bash
cd pygame_haxima
pip install -e .[dev]
```

### Run

```bash
cd pygame_haxima
python -m pygame_haxima
```

### Test

```bash
cd pygame_haxima
python -m pytest
```

### Key Controls

- Move: Arrow keys or WASD
- Talk: `t`
- Open chest: `o`
- Get items: `g`
- Attack: `f`
- Cast selected spell: `c`
- Cycle spell: `v`
- Examine: `x`
- Options panel: `F10`
- Save / Load: `F5` / `F9`
- Confirm target: `Enter` or `Space`
- Cancel target: `Esc`

Debug overlays:

- Terrain overlay: `F2`
- Sprite warning overlay: `F3`
- Runtime state overlay: `F4`

On startup, the Pygame port also writes a sprite coverage report to:

- `pygame_haxima/reports/sprite_coverage_report.txt`

## Legacy C/SDL Engine

The original engine source is in `src/`.

Build and installation details for the legacy engine are documented in `INSTALL`.

## Documentation

- Player guide: `doc/USERS_GUIDE`
- Additional docs: `doc/`
- Pygame port notes: `pygame_haxima/README.md`

## Repository Layout

- `pygame_haxima/`: modern Python/Pygame port (recommended)
- `src/`: original C/SDL engine
- `worlds/`: game world data
- `doc/`: player and developer documentation
- `scripts/`: utility and maintenance scripts
