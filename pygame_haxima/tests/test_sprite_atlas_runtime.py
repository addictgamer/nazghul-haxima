from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.data.sprite_atlas import SpriteAtlas


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
