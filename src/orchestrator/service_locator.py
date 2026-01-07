"""
Service Locator - Find where services should be located in the workspace

Provides codebase awareness to determine correct service locations.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# SPECTRA organization folders (from workspace structure)
SPECTRA_ORG_FOLDERS = ["Core", "Data", "Design", "Engagement", "Engineering", "Media", "Security"]


class ServiceLocator:
    """Locate services in the SPECTRA workspace."""

    def __init__(self, workspace_root: Path):
        """
        Initialize service locator.
        
        Args:
            workspace_root: SPECTRA workspace root directory
        """
        self.workspace_root = workspace_root

    def find_service_directory(self, service_name: str) -> Optional[Path]:
        """
        Find existing service directory across all org folders.
        
        Args:
            service_name: Service name to locate
            
        Returns:
            Path to service directory if found, None otherwise
        """
        for org_folder in SPECTRA_ORG_FOLDERS:
            service_dir = self.workspace_root / org_folder / service_name
            if service_dir.exists() and service_dir.is_dir():
                logger.debug(f"Found service '{service_name}' in {org_folder}/")
                return service_dir
        
        logger.debug(f"Service '{service_name}' not found in any org folder")
        return None

    def get_service_location(
        self, service_name: str, service_type: Optional[str] = None
    ) -> Tuple[Path, str]:
        """
        Determine where a service should be located.
        
        Logic:
        1. If service exists, use existing location
        2. If service_type indicates org (e.g., "data-service" -> Data)
        3. Default to Core for services, Data for data-related
        
        Args:
            service_name: Service name
            service_type: Service type (service, tool, package, concept)
            
        Returns:
            Tuple of (service_directory_path, org_folder_name)
        """
        # First, check if service already exists
        existing_dir = self.find_service_directory(service_name)
        if existing_dir:
            org_folder = existing_dir.parent.name
            return existing_dir, org_folder

        # Determine org folder based on service type/name
        org_folder = self._determine_org_folder(service_name, service_type)
        service_dir = self.workspace_root / org_folder / service_name
        
        return service_dir, org_folder

    def _determine_org_folder(self, service_name: str, service_type: Optional[str] = None) -> str:
        """
        Determine which org folder a service should go in.
        
        Args:
            service_name: Service name
            service_type: Service type
            
        Returns:
            Org folder name
        """
        # Data-related services go to Data
        data_keywords = ["data", "pipeline", "fabric", "lakehouse", "warehouse", "etl", "transform"]
        if any(keyword in service_name.lower() for keyword in data_keywords):
            return "Data"
        
        # Design-related (future)
        if service_type == "design" or "design" in service_name.lower():
            return "Design"
        
        # Default to Core for most services
        return "Core"

    def get_document_directory(
        self, service_name: str, document_type: str, service_type: Optional[str] = None, create: bool = True
    ) -> Path:
        """
        Get the appropriate directory for service documents.
        
        Discovery documents are client-facing and should be part of the service.
        We create the service directory structure during discovery if needed.
        
        .spectra/ is for orchestrator execution state (manifests, history, cache),
        not for client-facing service documents.
        
        Args:
            service_name: Service name
            document_type: Type of document (discovery, design, etc.)
            service_type: Service type (optional, helps determine location)
            create: Whether to create the directory structure if it doesn't exist
            
        Returns:
            Path to document directory (service directory)
        """
        service_dir, org_folder = self.get_service_location(service_name, service_type)
        
        # Use service directory structure (create if needed)
        # Discovery documents are service artifacts, not orchestrator cache
        docs_dir = service_dir / "docs" / document_type
        
        if create:
            docs_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Using service directory for {document_type} docs: {org_folder}/{service_name}/docs/{document_type}")
        
        return docs_dir

    def get_specification_path(self, service_name: str, service_type: Optional[str] = None) -> Path:
        """
        Get path for specification file (SPECTRA-Grade: in service directory).
        
        SPECTRA Service Blueprint: {service}/{service}.specification.yaml
        
        Args:
            service_name: Service name
            service_type: Service type
            
        Returns:
            Path to specification file in service directory
        """
        service_dir, _ = self.get_service_location(service_name, service_type)
        # SPECTRA-Grade: Follows Service Blueprint naming: {service}/{service}.specification.yaml
        return service_dir / f"{service_name}.specification.yaml"

