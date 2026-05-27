from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.scm_converter import ScmConverter


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    world = root.parent / "worlds" / "haxima-1.002"
    output = root / "converted_data"
    converter = ScmConverter()

    targets = [
        "terrains.scm",
        "zones.scm",
        "world-map.scm",
    ]
    for rel in targets:
        src = world / rel
        if not src.exists():
            print(f"skip: {src}")
            continue
        dst = output / f"{src.stem}.json"
        count = converter.convert_defines(src, dst)
        print(f"converted {src.name}: {count} defines -> {dst.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
