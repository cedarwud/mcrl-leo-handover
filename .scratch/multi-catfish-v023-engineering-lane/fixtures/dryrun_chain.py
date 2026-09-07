from __future__ import annotations

import hashlib
from pathlib import Path


def authenticate(root: Path) -> Path:
    if not root.is_dir():
        raise ValueError("artifact root is absent")
    return root


def load(authenticated: Path) -> str:
    return (authenticated / "payload.txt").read_text(encoding="utf-8")


def merge(payload: str, destination: Path) -> Path:
    destination.write_text(payload + "|merged", encoding="utf-8")
    return destination


def seal_verify(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Provider:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.cursor = 0

    def next_batch(self, *, route: str, source: str, update_cursor: int) -> dict[str, object]:
        if (route, source, update_cursor) != ("C1", "informed", self.cursor):
            raise ValueError("deterministic provider order drifted")
        self.cursor += 1
        return {"route": route, "source": source, "payload": self.payload}


def make_provider(payload: str) -> Provider:
    return Provider(payload)


class Runner:
    def __init__(self, provider: Provider) -> None:
        self.provider = provider
        self.epochs = 0

    def one_epoch(self, batch: dict[str, object]) -> int:
        if batch["route"] != "C1":
            raise ValueError("route drifted")
        self.epochs += 1
        return self.epochs

    def export(self, path: Path) -> Path:
        path.write_text(str(self.epochs), encoding="ascii")
        return path

    def resume(self) -> int:
        self.epochs += 1
        return self.epochs


def make_runner(provider: Provider) -> Runner:
    return Runner(provider)


def reload_runner(path: Path, provider: Provider) -> Runner:
    runner = Runner(provider)
    runner.epochs = int(path.read_text(encoding="ascii"))
    return runner


def attempt_input_write(root: Path) -> None:
    (root / "payload.txt").write_text("mutated", encoding="utf-8")


def consume_missing(value: object) -> object:
    return value
