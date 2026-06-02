# Zone-by-zone content porting

This project keeps Phase 4 in-tree so Haxima content can be migrated incrementally.

## Current tools

- `pygame_haxima.data.scm_parser.ScmParser`: tokenizes and parses nested Scheme S-expressions.
- `pygame_haxima.data.scm_converter.ScmConverter`: converts parsed Scheme into JSON outputs, including a runtime terrain registry from `terrains.scm`.
- `pygame_haxima.data.scheme_bridge.SchemeBridge`: interface stub for a future embedded Scheme runtime.

## Suggested sequence

1. `worlds/haxima-1.002/terrains.scm` -> terrain registry JSON
2. `worlds/haxima-1.002/palette.scm` -> palette token map JSON (`converted_data/palettes.runtime.json`)
3. `worlds/haxima-1.002/maps/*.scm` -> static map JSON chunks (`converted_data/maps/*.map.json`)
4. `worlds/haxima-1.002/places/*.scm` -> place metadata and `(put …)` placements (`placements` in `converted_data/places/*.place.json`; runtime via `place_placements.py`)
5. `worlds/haxima-1.002/townsfolk/*.scm` (plus loaded files) -> NPC conversation/schedule/factory metadata (`converted_data/townsfolk.runtime.json`)
6. `worlds/haxima-1.002/quests-*.scm` -> quest metadata/state-transition scaffolds (`converted_data/quests/*.quests.json`)

Runtime loading (Pygame):

- `pygame_haxima.data.place_loader` builds explorable places from converted map + palette + terrain data.
- `HAXIMA_PLACE=cloviskeep` starts in converted Cloviskeep; default is tutorial slice.
- In-game **F6** travels between tutorial wilderness and Cloviskeep (dev/content preview).
- Cloviskeep: wyrm spawn, drawbridge gate tile, lever (**O** to toggle). Saves store `place_id` and reload the correct zone.

## Immediate command

```bash
cd pygame_haxima
python3 -m pygame_haxima.tools.zone_port
```

This command writes a validation artifact at
`converted_data/import_validation_report.json` with conversion counts, basic map
dimension checks, unresolved townsfolk load warnings, and quest export coverage.
