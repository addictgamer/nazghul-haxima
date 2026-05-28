# Zone-by-zone content porting

This project keeps Phase 4 in-tree so Haxima content can be migrated incrementally.

## Current tools

- `pygame_haxima.data.scm_parser.ScmParser`: tokenizes and parses nested Scheme S-expressions.
- `pygame_haxima.data.scm_converter.ScmConverter`: converts parsed Scheme into JSON outputs, including a runtime terrain registry from `terrains.scm`.
- `pygame_haxima.data.scheme_bridge.SchemeBridge`: interface stub for a future embedded Scheme runtime.

## Suggested sequence

1. `worlds/haxima-1.002/terrains.scm` -> terrain registry JSON
2. `worlds/haxima-1.002/maps/*.scm` -> static map JSON chunks (`converted_data/maps/*.map.json`)
3. `worlds/haxima-1.002/places/*.scm` -> place metadata and placement (`converted_data/places/*.place.json`)
4. `worlds/haxima-1.002/townsfolk/*.scm` (plus loaded files) -> NPC conversation/schedule/factory metadata (`converted_data/townsfolk.runtime.json`)
5. `worlds/haxima-1.002/quests-*.scm` -> quest logic and state transitions

## Immediate command

```bash
cd pygame_haxima
python3 -m pygame_haxima.tools.zone_port
```

This command writes a validation artifact at
`converted_data/import_validation_report.json` with conversion counts, basic map
dimension checks, and unresolved townsfolk load warnings.
