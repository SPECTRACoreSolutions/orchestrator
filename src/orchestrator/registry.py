"""
Registry Check - Anti-duplication utility

Checks service registry to prevent duplicate services.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class RegistryCheck:
    """Registry check utility for anti-duplication."""

    def __init__(self, workspace_root: Path):
        """
        Initialize registry check.
        
        Args:
            workspace_root: SPECTRA workspace root directory
        """
        self.workspace_root = workspace_root
        self.registry_path = workspace_root / "Core" / "registries" / "service-catalog.yaml"

    def check_service(self, service_name: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if service exists in registry.
        
        Args:
            service_name: Service name to check
            
        Returns:
            Tuple of (exists: bool, service_info: Optional[Dict])
        """
        if not self.registry_path.exists():
            logger.warning(f"Registry not found at {self.registry_path}, skipping check")
            return False, None

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = yaml.safe_load(f) or {}

            # Check in both staging and production
            for workspace in ["cosmos"]:  # Can extend to other workspaces
                for environment in ["staging", "production"]:
                    services = registry.get(workspace, {}).get(environment, {}).get("services", [])
                    for service in services:
                        if service.get("name") == service_name:
                            logger.info(f"Service '{service_name}' found in {workspace}/{environment}")
                            return True, {
                                "name": service.get("name"),
                                "url": service.get("url"),
                                "status": service.get("status"),
                                "version": service.get("version"),
                                "workspace": workspace,
                                "environment": environment,
                            }

            logger.info(f"Service '{service_name}' not found in registry (new service)")
            return False, None

        except Exception as e:
            logger.warning(f"Registry check failed: {e}")
            return False, None

    def should_block(self, service_info: Optional[Dict]) -> bool:
        """
        Determine if service creation should be blocked.
        
        Blocks if service exists and is healthy (zero tolerance for duplicates).
        
        Args:
            service_info: Service information from registry
            
        Returns:
            True if should block, False otherwise
        """
        if not service_info:
            return False

        # Block if service is healthy
        if service_info.get("status") == "healthy":
            return True

        return False

