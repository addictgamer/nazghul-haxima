from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.data.sprite_atlas import SpriteAtlas, SpriteRef


def test_runtime_coverage_classifies_aliases_and_missing(tmp_path) -> None:
    atlas = SpriteAtlas(asset_loader=AssetLoader(tmp_path), project_root=Path(tmp_path))
    atlas.refs = {
        "s_wolf": object(),  # type: ignore[assignment]
        "s_old_townsman": object(),  # type: ignore[assignment]
    }
    atlas.surfaces = {"s_grass": atlas._fallback_surface("s_grass")}
    atlas.fallback_keys = {"s_old_townsman"}

    report = atlas.runtime_coverage_report(
        ["s_wolf_n", "s_old_townsman", "s_guard-n", "s_mystery", "s_grass"]
    )

    assert "s_old_townsman" in report["direct_resolved"]
    assert report["alias_resolved"]["s_wolf_n"] == "s_wolf"
    assert report["unresolved_aliases"]["s_guard-n"] == "s_guard_n"
    assert "s_mystery" in report["missing_runtime_keys"]
    # Direct fallback and alias-to-fallback both count as runtime fallback usage.
    assert "s_old_townsman" in report["fallback_runtime_keys"]


def test_get_for_tick_uses_multiframe_variants_and_caches(tmp_path, monkeypatch) -> None:
    atlas = SpriteAtlas(asset_loader=AssetLoader(tmp_path), project_root=Path(tmp_path))
    atlas.refs = {"s_wolf": SpriteRef(key="s_wolf", sprite_set="ss_test", frame_count=3, tile_index=10)}
    atlas.surfaces = {
        "s_grass": object(),  # type: ignore[assignment]
        "s_wolf": object(),  # type: ignore[assignment]
    }

    calls: list[int] = []

    def _fake_extract(key: str, frame_offset: int):
        calls.append(frame_offset)
        return object(), None  # type: ignore[return-value]

    monkeypatch.setattr(atlas, "_extract_surface_for_frame", _fake_extract)

    # Tick chooses frame 1 (10 // 8 => 1).
    frame_surface = atlas.get_for_tick("s_wolf", tick=10, frame_stride=8)
    assert calls == [1]

    # Same frame should hit cache and avoid another extract call.
    cached_surface = atlas.get_for_tick("s_wolf", tick=10, frame_stride=8)
    assert frame_surface is cached_surface
    assert calls == [1]


def test_parse_sprite_refs_supports_spell_macro_lines(tmp_path, monkeypatch) -> None:
    atlas = SpriteAtlas(asset_loader=AssetLoader(tmp_path), project_root=Path(tmp_path))
    fake_path = Path(tmp_path) / "worlds" / "haxima-1.002" / "spells.scm"
    monkeypatch.setattr(atlas, "_iter_world_scm_paths", lambda: [fake_path])
    monkeypatch.setattr(
        atlas,
        "_active_lines",
        lambda _path: [
            "(mk-sprite 's_grav_por          2)",
            "(mk-sprite 's_mani              4)",
        ],
    )

    atlas._parse_sprite_refs()

    assert atlas.refs["s_grav_por"].sprite_set == "ss_spells"
    assert atlas.refs["s_grav_por"].tile_index == 2
    assert atlas.refs["s_mani"].tile_index == 4
