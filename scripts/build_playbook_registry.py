"""
Build Playbook Registry - Scan playbooks and create registry YAML

Scans Core/operations/playbooks/ and creates playbooks-registry.yaml
"""

import yaml
from pathlib import Path
from typing import Dict, List

def extract_activity_from_path(path: Path, domain: str) -> str:
    """Extract activity name from playbook path/domain."""
    # Map domains to activities
    domain_to_activity = {
        "railway": "provision",  # Or "deploy"
        "github": "provision",
        "dataverse": "provision",
        "fabric": "provision",
        "identity": "provision",
        "build": "build",
        "test": "test",
        "deploy": "deploy",
        "monitor": "monitor",
        "release": "finalise",
    }

    # Check filename for activity hints
    name_lower = path.stem.lower()
    if "deploy" in name_lower or "deployment" in name_lower:
        return "deploy"
    if "build" in name_lower or "compile" in name_lower:
        return "build"
    if "test" in name_lower:
        return "test"
    if "monitor" in name_lower or "health" in name_lower:
        return "monitor"
    if "setup" in name_lower or "configure" in name_lower:
        return "provision"
    if "release" in name_lower or "final" in name_lower:
        return "finalise"

    return domain_to_activity.get(domain, "provision")  # Default to provision

def scan_playbooks(workspace_root: Path) -> List[Dict]:
    """Scan all playbooks and extract metadata."""
    playbooks_dir = workspace_root / "Core" / "operations" / "playbooks"
    playbooks = []

    for playbook_path in playbooks_dir.rglob("*.md"):
        # Skip README and structure files
        if playbook_path.name in ["README.md", "structure.md", "MIGRATION-LOG.md"]:
            continue

        # Determine domain from path
        relative_path = playbook_path.relative_to(playbooks_dir)
        path_parts = relative_path.parts

        if len(path_parts) > 1:
            domain = path_parts[0]
        else:
            domain = "general"

        # Extract activity
        activity = extract_activity_from_path(playbook_path, domain)

        # Read first few lines to get description
        try:
            with open(playbook_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]
                description = ""
                for line in lines:
                    if line.strip().startswith('#') or line.strip().startswith('##'):
                        description = line.strip('#').strip()
                        break
                if not description:
                    description = playbook_path.stem.replace('-', ' ').replace('_', ' ').title()
        except Exception:
            description = playbook_path.stem.replace('-', ' ').title()

        playbook_entry = {
            "name": playbook_path.stem,
            "description": description[:200],  # Limit length
            "path": str(relative_path).replace('\\', '/'),
            "activity": activity,
            "domain": domain,
            "inputs": [],
            "outputs": [],
            "metadata": {
                "summary": description[:100],
                "mcp_native": "railway" in domain or "github" in domain,
                "manual_steps": False,
                "automation_possible": True,
            }
        }

        playbooks.append(playbook_entry)

    return playbooks

def build_registry(workspace_root: Path) -> Dict:
    """Build playbook registry."""
    playbooks = scan_playbooks(workspace_root)

    registry = {
        "version": "1.0",
        "generated_at": "2026-01-08T00:00:00Z",
        "playbooks": sorted(playbooks, key=lambda x: (x["domain"], x["name"]))
    }

    return registry

def main():
    """Build and save playbook registry."""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    workspace_root = Path(__file__).parent.parent.parent.parent

    registry = build_registry(workspace_root)

    registry_path = workspace_root / "Core" / "operations" / "playbooks" / "playbooks-registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    with open(registry_path, 'w', encoding='utf-8') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Created playbook registry: {registry_path}")
    print(f"   Found {len(registry['playbooks'])} playbooks")
    print(f"   Domains: {sorted(set(p['domain'] for p in registry['playbooks']))}")

if __name__ == "__main__":
    main()

