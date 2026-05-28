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
- Camera now uses clamped deadzone-follow behavior for larger maps, reducing constant recentering while preserving edge clamping.
- Selection highlight polish now includes pulsing target cursor, valid-target overlays, and a target trail from party to cursor.
- Party rendering now uses the lead member sprite key (`s_wanderer` in tutorial) instead of a hardcoded placeholder key.
- Startup UI scale now prefers `2x` and automatically falls back to `1x` when `2x` would exceed desktop resolution.
- Actor collision blocking now prevents party/monsters from stepping onto occupied actor tiles, and combat feedback banners are larger/higher-contrast for readability.
- Combat feedback banners now support semi-transparency and world-anchor positioning near the relevant combatant tile.
- M4 kickoff complete: nested Scheme parser added, and `terrains.scm` now converts into a runtime terrain registry JSON.
- Parser-backed map converter now exports `maps/*.scm` into structured tile-layer JSON files plus an index.
- Parser-backed place converter now exports `places/*.scm` into structured place metadata JSON with hooks/subplace/object summaries.
- Parser-backed townsfolk converter now exports conversation keywords, schedule summaries, and NPC factory metadata from the `townsfolk/init.scm` load chain.
- Zone import command now writes `converted_data/import_validation_report.json` with per-section counts and validation warnings.
- Parser-backed quest converter now exports `quests-*.scm` metadata/update scaffolds into `converted_data/quests/*.quests.json` plus index coverage.
- Sprite parity workstream is now tracked explicitly (entity/object key parity, runtime coverage diagnostics, and fallback quality gates).
- Post-port conversation UX enhancement is logged: modal interactable dialogue vs anchored fade popups for one-off NPC utterances.
- Inventory UI now renders item icons in the console panel, and ground-item rendering shares the same item-to-sprite mapping helper.
- Added right-sidebar layout for character + inventory panels, separating them from console dialogue/log space.
- Save system now includes schema versioning, migration hooks, and corruption quarantine handling for safer loads.
- Save/load now includes a slot-selection modal (F5/F9) with keyboard navigation and per-slot summaries.
- Save/load slot modal now supports mouse click interactions and distinct row-card styling for clearer slot separation.
- Quest/NPC debug state display is now gated behind a dedicated runtime debug toggle key (`F4`).
- UI layering fix: save/load modal now renders above the sidebar instead of being occluded by it.
- Content migration pipeline is only a starter scaffold (not full Scheme compatibility).
- Full Haxima content parity is **not** implemented yet.

## Milestone Status Board

| ID | Milestone | Status | Progress | Exit Criteria |
|---|---|---|---:|---|
| M0 | Build + launch tooling | Completed | 100% | `pygame.sh`, `pygame.bat`, `requirements.txt`, package entrypoints working |
| M1 | Engine foundation | Completed | 100% | Event loop, renderer, map draw, domain models, input wiring in place |
| M2 | Vertical slice gameplay | Completed | 100% | Tutorial map with move/talk/open/get/attack/examine/save/load |
| M3 | UX redesign pass | Completed | 100% | Scalable display, polished UI readability, robust mouse-target command UX |
| M4 | Content import pipeline | Completed | 100% | Reliable converters for terrain/map/place/NPC/quest data |
| M5 | Save/load robustness | Completed | 100% | Stable schema versioning + full world state restore |
| M6 | Testing + quality gates | Completed | 100% | Unit/integration tests + CI smoke run + regression suite |
| M7 | Full Haxima compatibility | In Progress | 18% | Main quest path playable with migrated content/system parity |
| M8 | Packaging + distribution | Not Started | 15% | Reproducible local builds, docs, release artifacts |

## What Remains To Implement

### M3: UX redesign pass (completed)

- [x] Add in-game menu/options screen for scale/fullscreen/keybinds.
- [x] Improve text system (font fallback + wrapping + dialogue panel behavior).
- [x] Implement command targeting UX parity (cursor mode, cancel/confirm flow, prompts).
- [x] Add terrain debug overlay toggle for visual map validation (`F2`).
- [x] Add sprite warning overlay toggle for fallback-key monitoring (`F3`).
- [x] Add visual polish: selection highlights, damage feedback, encounter indicators.
- [x] Improve camera behavior and clamping for larger places.

### M4: Content import pipeline

- [x] Replace regex converter with parser that can handle nested list structures from `.scm`.
- [x] Convert `terrains.scm` into runtime terrain registry with passability + visual mapping.
- [x] Convert `maps/*.scm` into tile layers compatible with renderer.
- [x] Convert `places/*.scm` into place metadata and placements.
- [x] Convert `townsfolk/*.scm` keyword/dialogue content.
- [x] Create zone-by-zone import command and validation report (sprite coverage + terrains/maps/places/townsfolk exports + indexes + `import_validation_report.json`).
- [x] Convert `quests-*.scm` into structured quest metadata/state-transition scaffolds.

### M5: Save/load robustness

- [x] Add save schema version field and migration hooks.
- [x] Persist/restore all mutable state (opened containers, NPC states, quest flags, time).
- [x] Ensure deterministic reload of combat/non-combat state.
- [x] Add corruption handling and recovery messages.

### M6: Testing + quality gates

- [x] Add pytest suite for domain logic (movement, passability, combat resolution, inventory).
- [x] Add integration tests for tutorial flow.
- [x] Add converter tests with fixture `.scm` files.
- [x] Add lint/test commands to documented workflow.
- [x] Add CI pipeline to run static checks + tests.

### M7: Full Haxima compatibility

- [~] Sprite parity pass (entity/object visuals beyond terrain):
  - [x] Pass 1: tutorial critical keys switched from placeholders to canonical keys (`s_wanderer`, `s_old_townsman`, `s_wolf`, `s_chest`).
  - [~] Pass 2: pull NPC/monster/object sprite keys from converted place/townsfolk content instead of hardcoded defaults *(runtime sprite profile now sourced from converted place/townsfolk outputs; broader zone-wide adoption pending)*.
  - [~] Pass 3: item sprite parity (ground pickups/containers/inventory categories) with canonical icon mappings.
  - [ ] Pass 4: extend coverage report to include non-terrain runtime keys and classify unresolved aliases.
  - [ ] Pass 5: add quality gate test for critical fallbacks (player/NPC/monster/chest/door/item categories).
  - [ ] Pass 6: directional/animation variants where source art supports it.
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
- Content conversion now handles selected structured forms, but broad Scheme semantics/behavior are still not interpreted.
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
- Improved camera UX for larger maps with deadzone-follow + strict world-edge clamping.
- Completed final M3 selection polish with pulsing target cursor, valid-target overlays, and party-to-target trail rendering.
- Kicked off M4: implemented a real S-expression parser and parser-backed conversion pipeline.
- Added parser-driven terrain export: `converted_data/terrains.runtime.json` now contains structured terrain definitions.
- Added parser-driven map export: `converted_data/maps/*.map.json` with row/tile layer data plus `converted_data/maps/index.json`.
- Added parser-driven place export: `converted_data/places/*.place.json` with place flags, hooks, and object/subplace summaries.
- Added parser-driven townsfolk export: `converted_data/townsfolk.runtime.json` with conversation keyword sets, schedules, and factory metadata (including `mk-abe` and `sch_abe` extraction).
- Added generated import validation report: `converted_data/import_validation_report.json` with coverage counters and conversion warnings.
- Added parser-driven quest exports: `converted_data/quests/*.quests.json` + `converted_data/quests/index.json` with `qst-mk` quest records and quest-data update references.
- Fixed missing player art by switching tutorial/player rendering from placeholder `s_party` to actual sprite key usage (`s_wanderer` / party lead sprite).
- Started sprite parity pass for non-terrain visuals by replacing tutorial placeholder entity keys (`s_npc`, `s_monster`) with canonical sprite keys and matching atlas fallbacks.
- Updated startup display behavior: default UI scale now auto-selects `2x` on large displays and `1x` on smaller desktops.
- Fixed movement overlap behavior (no actor tile-sharing during movement) and improved combat damage popup readability/visibility.
- Reanchored combat feedback popups to relevant world tiles (with clamping fallback) and tuned transparency for better map readability.
- Expanded sprite definition parsing to scan world `.scm` files beyond `sprites.scm`, enabling canonical item sprite keys from modules like `arms.scm` and `potions.scm`.
- Started item sprite parity implementation: chest-spilled ground items now render with item-key mapping (`s_dagger`, `s_leather_armor`, `s_healing_potion` fallbacks).
- Logged post-port dialogue UX split: modal conversations for interactables, anchored fade popups for one-off NPC lines.
- Added inventory icon strip in UI and unified item sprite lookup between map ground-item rendering and UI item display.
- Refactored layout to a dedicated sidebar for character stats and inventory so NPC dialogue and logs no longer compete for the same console space.
- Added save schema version (`save_version`), v0->v1 migration path, ground-item persistence, and corrupted-save quarantine with user-facing load error messaging.
- Expanded save payload restoration for key runtime session state (victory flag, targeting state, selected NPC, dialogue panel state) to improve continuity after reload.
- Added save/load slot modal UI (keyboard-driven) with slot metadata labels and explicit per-slot save/load actions.
- Added mouse support for save/load modal selection/actions and visually distinct slot rows with dedicated action buttons.
- Added optional runtime-state debug panel (quest flags + NPC states) hidden behind `F4` toggle.
- Fixed render order so modal UI layers (save/load/options) draw above sidebar panels.
- Added post-load normalization to reset transient UI/combat states (menus, targeting, popup feedback, camera) for deterministic resumes.
- Added NPC mutable-state + quest-flag scaffolding to runtime session and save payload, including state updates from talk/chest/combat events.
- Added persistence for NPC positions and runtime UI settings (scale/fullscreen/debug toggles/camera deadzone), plus post-load renderer sync to apply saved display state.
- Added save/load regression tests covering round-trip mutable-state persistence, v0->v1 migration defaults, and corrupted-save quarantine behavior.
- Updated README controls with the `F4` runtime debug toggle and documented local `pytest` test execution.
- Added tutorial integration tests for event-driven gameplay flow (talk, chest open/get loop, attack/victory transition, and actor-collision blocking).
- Added parser/converter fixture tests for terrains, maps, quests, and townsfolk load-chain extraction with passing local pytest run.
- Added GitHub Actions CI workflow to run Ruff + pytest on pushes and pull requests affecting the Pygame port.
- Expanded tutorial/domain test coverage for blocked wall movement, no-target action rejection, and non-lethal combat resolution; local suite now passes at 15 tests.
- Added converted-content sprite profile loading (townsfolk + places JSON) and wired tutorial NPC/monster/chest sprite assignment through profile-based resolution instead of direct hardcoded keys.
- Combat feedback popup now merges same-exchange player/enemy outcomes into a multi-line banner so both actions are visible at once.
- Combat feedback lines now include actor prefixes (`You:` / `<Enemy>:`) for faster scanability in multi-line exchange popups.
- Combat banner now resets at the start of each new attack exchange so prior-round lines never linger into subsequent rounds.
- Enemy death outcomes are now included in the combat banner (`<Enemy>: Falls`) so kill confirmations appear in-banner, not only in the log.

## Suggested Delivery Sequence

1. Continue M7 sprite parity pass so entity/object visuals are data-driven and fallback-safe.
2. Build M6 test/CI gates before larger compatibility work.
3. Iterate M7 zone-by-zone until main quest path is reachable.
4. Close with M8 release packaging and release process docs.

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
