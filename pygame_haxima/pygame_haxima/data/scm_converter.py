from __future__ import annotations

import json
import re
from pathlib import Path


class ScmConverter:
    """
    Minimal Phase-4 converter scaffold.

    This does not parse full Scheme. It extracts a few simple `(define key value)`
    declarations into JSON so data can be ported zone-by-zone.
    """

    DEFINE_RE = re.compile(r"\(define\s+(?P<name>[^\s\)]+)\s+(?P<value>[^\)]+)\)")

    def convert_defines(self, src: Path, dst: Path) -> int:
        text = src.read_text(encoding="utf-8", errors="ignore")
        out: dict[str, str] = {}
        for match in self.DEFINE_RE.finditer(text):
            out[match.group("name")] = match.group("value").strip()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return len(out)
