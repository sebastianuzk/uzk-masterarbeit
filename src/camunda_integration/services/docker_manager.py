
from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class DockerManager:
    compose_file: Path

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, check=True, capture_output=True, text=True)

    def up(self, detach: bool = True) -> str:
        args = ["docker", "compose", "-f", str(self.compose_file), "up"]
        if detach:
            args.append("-d")
        cp = self._run(args)
        return cp.stdout

    def down(self) -> str:
        cp = self._run(["docker", "compose", "-f", str(self.compose_file), "down"])
        return cp.stdout

    def restart(self) -> str:
        self.down()
        return self.up()

    def logs(self, service: Optional[str] = None, tail: str = "200") -> str:
        args = ["docker", "compose", "-f", str(self.compose_file), "logs", "--tail", tail]
        if service:
            args.append(service)
        cp = self._run(args)
        return cp.stdout
