# Pygame Haxima Milestones

This file tracks project status for the Pygame redesign of Nazghul/Haxima.

## Current Snapshot

- Project scaffold exists and runs through `pygame.sh` / `pygame.bat`.
- A playable tutorial-style vertical slice exists (movement, talk, chest, loot, basic combat, save/load).
- Rendering/UI foundation exists (map viewport + HUD + console + command bar).
- Terrain rendering now supports real sprite-sheet extraction from `sprite-sets.scm` + `sprites.scm` when art files are present, with fallback tiles otherwise.
- Terrain debug overlay exists (`F2`) for terrain-id validation during map tuning.
- Sprite coverage diagnostics now print at startup and write to `pygame_haxima/reports/sprite_coverage_report.txt`.
- Sprite warning overlay exists (`F3`) to show terrain fallback-key counts in-game.
- In-game options panel exists (`F10`) with scale/fullscreen/debug toggles and keybind preview.
- Command targeting flow now exists for talk/open/attack/examine with cursor move + confirm/cancel.
- Mouse-to-tile targeting now uses the same camera window math as map rendering (fixes cursor offset/misalignment).
- Short-range actions now fail fast when no in-range target exists and no longer allow out-of-range target selection.
- Text UI now has font fallback, width-aware wrapping, and a dedicated dialogue panel for NPC conversation lines.
- Console layout now dynamically clamps visible log lines when dialogue panel is present, preventing overlap with the command bar.
- Visual combat polish added: target cursor validity colors, nearby-hostile indicators, and transient hit/miss feedback banners.
- Targeting now auto-focuses a valid in-range target tile for short-range actions instead of defaulting to the player tile.
- Content migration pipeline is only a starter scaffold (not full Scheme compatibility).
- Full Haxima content parity is **not** implemented yet.

## Milestone Status Board

| ID | Milestone | Status | Progress | Exit Criteria |
|---|---|---|---:|---|
| M0 | Build + launch tooling | Completed | 100% | `pygame.sh`, `pygame.bat`, `requirements.txt`, package entrypoints working |
| M1 | Engine foundation | Completed | 100% | Event loop, renderer, map draw, domain models, input wiring in place |
| M2 | Vertical slice gameplay | Completed | 100% | Tutorial map with move/talk/open/get/attack/examine/save/load |
| M3 | UX redesign pass | In Progress | 90% | Scalable display, polished UI readability, robust mouse-target command UX |
| M4 | Content import pipeline | In Progress | 35% | Reliable converters for terrain/map/place/NPC/quest data |
| M5 | Save/load robustness | In Progress | 35% | Stable schema versioning + full world state restore |
| M6 | Testing + quality gates | Not Started | 10% | Unit/integration tests + CI smoke run + regression suite |
| M7 | Full Haxima compatibility | Not Started | 5% | Main quest path playable with migrated content/system parity |
| M8 | Packaging + distribution | Not Started | 15% | Reproducible local builds, docs, release artifacts |

## What Remains To Implement

### M3: UX redesign pass (next major deliverable)

- [x] Add in-game menu/options screen for scale/fullscreen/keybinds.
- [x] Improve text system (font fallback + wrapping + dialogue panel behavior).
- [x] Implement command targeting UX parity (cursor mode, cancel/confirm flow, prompts).
- [x] Add terrain debug overlay toggle for visual map validation (`F2`).
- [x] Add sprite warning overlay toggle for fallback-key monitoring (`F3`).
- [~] Add visual polish: selection highlights, damage feedback, encounter indicators (implemented for targeting/combat core loop; further effects optional).
- [ ] Improve camera behavior and clamping for larger places.

### M4: Content import pipeline

- [ ] Replace regex converter with parser that can handle nested list structures from `.scm`.
- [~] Convert `terrains.scm` into runtime terrain registry with passability + visual mapping (sprite-key mapping started in tutorial terrain defs).
- [ ] Convert `maps/*.scm` into tile layers compatible with renderer.
- [ ] Convert `places/*.scm` into place metadata and placements.
- [ ] Convert `townsfolk/*.scm` keyword/dialogue content.
- [~] Create zone-by-zone import command and validation report (startup sprite coverage report added).

### M5: Save/load robustness

- [ ] Add save schema version field and migration hooks.
- [ ] Persist/restore all mutable state (opened containers, NPC states, quest flags, time).
- [ ] Ensure deterministic reload of combat/non-combat state.
- [ ] Add corruption handling and recovery messages.

### M6: Testing + quality gates

- [ ] Add pytest suite for domain logic (movement, passability, combat resolution, inventory).
- [ ] Add integration tests for tutorial flow.
- [ ] Add converter tests with fixture `.scm` files.
- [ ] Add lint/test commands to documented workflow.
- [ ] Add CI pipeline to run static checks + tests.

### M7: Full Haxima compatibility

- [ ] Implement spell system parity (`spells.scm` + reagents behavior).
- [ ] Implement vehicle system.
- [ ] Implement diplomacy/faction mechanics.
- [ ] Implement quest engine and scripted world events.
- [ ] Implement broader world map + zone transitions.
- [ ] Reach “main quest playable” milestone from migrated content.

### M8: Packaging + distribution

- [ ] Document first-time setup for Linux/Windows.
- [ ] Add reproducible dependency lock strategy.
- [ ] Provide one-command dev bootstrap and debug profile mode.
- [ ] Prepare release notes template and changelog process.

## Technical Debt / Known Gaps

- Sprite-sheet extraction is implemented, but asset availability/mapping coverage is incomplete and still falls back for missing files/keys.
- Asset loading had a startup ordering bug (`convert_alpha()` before display init) and is now guarded; keep this invariant when refactoring init order.
- Scheme bridge is currently an interface stub, not an embedded interpreter.
- Content conversion currently extracts only simple `(define ...)` forms.
- Test coverage is minimal.
- Audio references exist but no verified asset compatibility matrix yet.

## Recent Updates

- Added cross-platform launch scripts and dependency bootstrap:
  - `pygame.sh`
  - `pygame.bat`
  - `requirements.txt`
- Added terrain sprite pipeline:
  - Sprite set parsing from `worlds/haxima-1.002/sprite-sets.scm`
  - Sprite mapping parsing from `worlds/haxima-1.002/sprites.scm`
  - Runtime tile extraction with safe fallback surfaces
- Added terrain debug overlay toggle (`F2`) and control docs update.
- Fixed startup crash caused by calling `convert_alpha()` before a display surface existed.
- Added startup sprite coverage summary + report file output (`pygame_haxima/reports/sprite_coverage_report.txt`).
- Added sprite warning overlay toggle (`F3`) for terrain fallback diagnostics.
- Added in-game options panel (`F10`) for scale/fullscreen/debug toggles plus keybind preview.
- Added command targeting cursor flow for `talk/open/attack/examine` (`Enter` confirm, `Esc` cancel, mouse target support).
- Fixed mouse targeting offset by unifying renderer click conversion with map camera viewport origin/clamping.
- Improved targeting QoL: in-range validation on action start and constrained cursor/mouse selection for short-range actions.
- Improved text system with font fallback stack, wrapped console rendering, and dialogue panel presentation.
- Fixed console/log overlap bug where dialogue panel could push log lines underneath the bottom command bar.
- Added visual combat UX polish: valid/invalid target coloring, adjacent hostile indicators, and fading hit/miss feedback banners.
- Improved target UX: when entering `talk/open/attack`, cursor now starts on a valid nearby target if one exists.

## Suggested Delivery Sequence

1. Finish M3 (UX polish + command targeting).
2. Advance M4 enough to load at least one authentic converted zone.
3. Complete M5 so converted zones are safely playable/saveable.
4. Build M6 test/CI gates before larger content migration.
5. Iterate M7 zone-by-zone until main quest path is reachable.
6. Close with M8 release packaging.

## Practical Definition of “Playable Alpha”

All must be true:

- [ ] One authentic converted Haxima zone loads from converted data.
- [ ] Dialogue, looting, and combat loop works without manual data patches.
- [ ] Save/load survives full gameplay cycle in that zone.
- [ ] Basic automated tests pass locally.
- [ ] Linux + Windows launch scripts both verified.

## Practical Definition of “Full Port”

All must be true:

- [ ] Main quest path can be completed in Pygame build.
- [ ] Core systems parity: movement, combat, dialogue, items, spells, quests, zones.
- [ ] Converted content pipeline is repeatable and documented.
- [ ] Regression suite covers critical gameplay loops.
- [ ] Release build and onboarding docs are complete.
