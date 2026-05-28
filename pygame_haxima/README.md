# pygame-haxima

Pygame-based redesign of the Nazghul/Haxima RPG.

## Run

```bash
cd pygame_haxima
python -m pygame_haxima
```

## Controls

- Move: arrows or WASD
- Talk: `t`
- Open chest: `o`
- Get items: `g`
- Attack: `f`
- Cast Spark: `c` (uses `sulphurous_ash`)
- Examine: `x`
- Options panel: `F10`
- Terrain debug overlay: `F2`
- Sprite warning overlay: `F3`
- Runtime state debug overlay: `F4`
- Save/load: `F5` / `F9`
- Target confirm: `Enter` (or `Space`)
- Target cancel: `Esc`

Spell notes:

- `Spark` is currently available on `c` (range 2), consumes `sulphurous_ash`.

On startup, the game prints a sprite coverage summary and writes:

- `pygame_haxima/reports/sprite_coverage_report.txt`

The report now includes:

- Base atlas coverage (`sprite_sets`, `sprite_refs`, fallback causes)
- Runtime sprite coverage (tutorial runtime + converted place/townsfolk/quest probes, alias resolutions, unresolved aliases)

Conversation lines now appear in a dedicated dialogue panel above the console log.

## Tests

```bash
cd pygame_haxima
python -m pytest
```
