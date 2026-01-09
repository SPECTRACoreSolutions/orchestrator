# ADR-005: Separate Assess Activity

**Status**: Accepted  
**Date**: 2026-01-06  
**Deciders**: Architecture Team

---

## Context

In solution-engine, maturity assessment was part of the Discover stage. However, maturity assessment:
- Can be useful at multiple points in the pipeline
- Benefits from different context (problem only → design → built artifact)
- Could be used for auditing existing services

---

## Decision

Extract maturity assessment into a separate Assess activity (class name: `Assess`, activity name: `"assess"`). Assess can be invoked:
- **Early Pipeline**: Initial maturity estimate (after Discover)
- **Mid-Pipeline**: Detailed assessment (after Design, with architecture context)
- **Post-Build/Deploy**: Audit what was actually built
- **Standalone**: On-demand maturity assessment for existing services
- **Continuous**: Periodic re-assessment as services evolve

---

## Consequences

### Positive

- **Separation of Concerns**: Discovery focuses on problem/idea, Assess on maturity
- **Flexibility**: Can assess at any point in pipeline
- **Reusability**: Same activity for new services, existing services, audits
- **Context-Aware**: Assessment adapts to available context

### Negative

- **Additional Activity**: More activities to orchestrate
- **Potential Duplication**: If always run immediately after Discover (but serves different purpose)

---

## Implementation

Assess will:
- Accept context (specification, manifest, design if available, built artifacts if available)
- Assess maturity level (L1-L7) based on available context
- Return maturity assessment with gap analysis (if current state available)

---

## Notes

This aligns with orchestrator's composable activity architecture and enables more flexible maturity assessment workflows.

