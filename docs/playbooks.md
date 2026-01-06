# Playbook Development Guide

**Status**: Draft  
**Last Updated**: 2026-01-06

## Overview

Playbooks are executable units (scripts, commands, workflows) that activities orchestrate. The playbook registry (`operations/playbooks/playbooks-registry.yaml`) is the single source of truth.

## Playbook Registry

Registry-driven discovery. All playbooks defined in `operations/playbooks/playbooks-registry.yaml`.

## Adding Playbooks

1. Add entry to `operations/playbooks/playbooks-registry.yaml`
2. Define playbook metadata (name, description, path, inputs, outputs)
3. Implement playbook (Python script, PowerShell, shell command)
4. Test playbook execution

## Playbook Format

```yaml
playbooks:
  - name: playbook-name
    description: "What this playbook does"
    path: "operations/playbooks/category/playbook.ps1"
    activity: "discover"  # Which activities can use this
    inputs:
      - name: input1
        type: string
    outputs:
      - name: output1
        type: string
```

