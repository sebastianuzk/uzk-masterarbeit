"""
Docker Manager for Camunda Platform 7

Manages Docker containers for Camunda Platform 7 using docker-compose.
"""

import logging
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class DockerManager:
    """
    Manages Camunda Docker containers
    """
    
    def __init__(self, compose_file_path: Optional[str] = None):
        """
        Initialize Docker manager
        
        Args:
            compose_file_path: Path to docker-compose.yml file
        """
        if compose_file_path:
            self.compose_file = Path(compose_file_path)
        else:
            # Default to our docker-compose file
            current_dir = Path(__file__).parent.parent
            self.compose_file = current_dir / "docker" / "docker-compose.yml"
        
        self.compose_dir = self.compose_file.parent
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_compose_available(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            # Try docker compose (newer syntax)
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            except Exception:
                return False
    
    def get_compose_command(self) -> List[str]:
        """Get the correct docker-compose command"""
        # Try new syntax first
        try:
            result = subprocess.run(
                ["docker", "compose", "version"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return ["docker", "compose"]
        except Exception:
            pass
        
        # Fallback to old syntax
        return ["docker-compose"]
    
    def start_camunda(self, detached: bool = True) -> Dict[str, Any]:
        """
        Start Camunda containers
        
        Args:
            detached: Run in background
            
        Returns:
            Result dictionary with status and output
        """
        if not self.is_docker_available():
            return {
                "success": False,
                "error": "Docker not available",
                "output": ""
            }
        
        if not self.is_compose_available():
            return {
                "success": False,
                "error": "Docker Compose not available", 
                "output": ""
            }
        
        if not self.compose_file.exists():
            return {
                "success": False,
                "error": f"docker-compose.yml not found at {self.compose_file}",
                "output": ""
            }
        
        try:
            cmd = self.get_compose_command() + [
                "-f", str(self.compose_file),
                "up"
            ]
            
            if detached:
                cmd.append("-d")
            
            logger.info(f"Starting Camunda with command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            return {
                "success": result.returncode == 0,
                "error": result.stderr if result.returncode != 0 else None,
                "output": result.stdout,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Docker startup timed out",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def stop_camunda(self) -> Dict[str, Any]:
        """
        Stop Camunda containers
        
        Returns:
            Result dictionary with status and output
        """
        try:
            cmd = self.get_compose_command() + [
                "-f", str(self.compose_file),
                "down"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "error": result.stderr if result.returncode != 0 else None,
                "output": result.stdout
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of Camunda containers
        
        Returns:
            Status dictionary
        """
        try:
            cmd = self.get_compose_command() + [
                "-f", str(self.compose_file),
                "ps"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "running": "camunda-platform" in result.stdout and "Up" in result.stdout
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "running": False
            }
    
    def get_logs(self, service: str = "camunda", lines: int = 50) -> Dict[str, Any]:
        """
        Get container logs
        
        Args:
            service: Service name
            lines: Number of lines to retrieve
            
        Returns:
            Logs dictionary
        """
        try:
            cmd = self.get_compose_command() + [
                "-f", str(self.compose_file),
                "logs", "--tail", str(lines), service
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "logs": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "logs": "",
                "error": str(e)
            }
    
    def restart_camunda(self) -> Dict[str, Any]:
        """
        Restart Camunda containers
        
        Returns:
            Result dictionary
        """
        # Stop first
        stop_result = self.stop_camunda()
        if not stop_result["success"]:
            return stop_result
        
        # Wait a moment
        time.sleep(2)
        
        # Start again
        return self.start_camunda()
    
    def pull_images(self) -> Dict[str, Any]:
        """
        Pull latest Docker images
        
        Returns:
            Result dictionary
        """
        try:
            cmd = self.get_compose_command() + [
                "-f", str(self.compose_file),
                "pull"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for pulling
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }