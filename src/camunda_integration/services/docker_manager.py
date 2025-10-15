
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

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
            subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_status(self) -> dict:
        """Get status of Docker containers"""
        try:
            cp = subprocess.run([
                "docker", "compose", "-f", str(self.compose_file), "ps", "--format", "json"
            ], capture_output=True, text=True, check=False)
            
            if cp.returncode != 0:
                return {"running": False, "containers": [], "error": cp.stderr}
            
            import json
            containers = []
            if cp.stdout.strip():
                for line in cp.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            containers.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            
            running = any(c.get("State", "").lower() == "running" for c in containers)
            return {
                "running": running,
                "containers": containers,
                "error": None
            }
        except Exception as e:
            return {"running": False, "containers": [], "error": str(e)}

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

    def start_camunda(self, detached: bool = True) -> dict:
        """Start Camunda containers"""
        try:
            output = self.up(detach=detached)
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart_camunda(self) -> dict:
        """Restart Camunda containers"""
        try:
            output = self.restart()
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_camunda(self) -> dict:
        """Stop Camunda containers"""
        try:
            output = self.down()
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_logs(self, service: Optional[str] = None, tail: str = "200") -> dict:
        """Get logs from containers"""
        try:
            output = self.logs(service=service, tail=tail)
            return {"success": True, "logs": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def logs(self, service: Optional[str] = None, tail: str = "200") -> str:
        args = ["docker", "compose", "-f", str(self.compose_file), "logs", "--tail", tail]
        if service:
            args.append(service)
        cp = self._run(args)
        return cp.stdout
