from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SchemeBridge:
    """
    Phase-4 bridge abstraction.

    Real interpreter embedding (s7/chibi-scheme) can implement this protocol
    without changing engine callers.
    """

    loaded_files: list[str] = field(default_factory=list)
    implemented_kern_calls: set[str] = field(default_factory=set)

    def load(self, rel_path: str) -> None:
        self.loaded_files.append(rel_path)

    def register_kern_call(self, name: str) -> None:
        self.implemented_kern_calls.add(name)

    def ready_for_bootstrap(self) -> bool:
        required = {"kern-load", "kern-set-clock", "kern-cfg-set"}
        return required.issubset(self.implemented_kern_calls)
