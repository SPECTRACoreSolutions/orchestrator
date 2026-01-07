# Discovery Activity Specification

## Purpose

The Discovery Activity is responsible for **deeply understanding problems, validating solutions, and uncovering comprehensive insights** about system requirements. It goes beyond simple extraction to provide a complete discovery analysis.

## Discovery Dimensions

Discovery should explore these 10 dimensions:

### 1. Problem Understanding
- **What problem are we solving?** Clear, specific problem statement
- **Who has this problem?** Stakeholders, users, affected parties
- **What's the impact?** High/Medium/Low, business impact, urgency
- **What's the root cause?** Why does this problem exist?

### 2. Current State
- **What exists now?** Current solutions, systems, processes
- **What's working?** Existing strengths
- **What's not working?** Pain points, limitations, gaps
- **What are the blockers?** Technical, organizational, process

### 3. Desired State
- **What do we want to achieve?** Vision, goals, objectives
- **What does success look like?** Success criteria, metrics, KPIs
- **What are the goals?** Short-term and long-term

### 4. Stakeholders
- **Who are the users?** Primary and secondary users
- **Who are the decision-makers?** Approvers, sponsors
- **Who benefits?** Direct and indirect beneficiaries
- **Who is affected?** Impacted parties (positive and negative)

### 5. Constraints
- **Technical constraints:** Platform, technology, infrastructure
- **Business constraints:** Budget, resources, timeline
- **Time constraints:** Deadlines, milestones, urgency
- **Compliance constraints:** Regulations, standards, policies

### 6. Requirements
- **Functional requirements:** What must the solution do?
- **Non-functional requirements:** Performance, security, scalability, reliability
- **Quality requirements:** Testing, documentation, maintainability

### 7. Risks
- **Technical risks:** Implementation challenges, technology risks
- **Business risks:** Market, financial, organizational risks
- **Implementation risks:** Timeline, resource, dependency risks

### 8. Alternatives
- **What other options exist?** Alternative solutions, approaches
- **Why this solution?** Rationale, comparison, trade-offs
- **What was considered?** Options evaluated and rejected

### 9. Solution Validation
- **Does the solution solve the problem?** Direct mapping
- **How does it solve it?** Mechanism, approach
- **What's the confidence level?** High/Medium/Low
- **What are the assumptions?** Key assumptions made

### 10. Next Steps
- **What happens next?** Pipeline progression
- **What activities are needed?** Assess, Build, Test, Deploy, etc.
- **What dependencies exist?** Prerequisites, blockers

## SPECTRA Standards

### Service Naming
- **Format:** Mononymic, kebab-case, lowercase
- **Examples:** `logging`, `user-auth`, `data-processor`
- **Invalid:** `spectra-logging-service`, `logging-service`, `LoggingService`
- **Rules:**
  - No `spectra-` prefix
  - No `-service` suffix
  - No action verbs (deploy, build, create)
  - No prepositions (to, from, in, on)
  - No reserved words (service, app, application, system)

### Service Types
- **service:** Microservice, API, backend service
- **tool:** CLI tool, utility, script
- **package:** Library, SDK, reusable component
- **concept:** Documentation, specification, design

### Maturity Levels
- **L1-MVP:** Minimum viable product
- **L2-Foundation:** Core functionality with basic quality
- **L3-Operational:** Production-ready with monitoring
- **L4-Optimised:** Performance optimised, scalable
- **L5-Intelligent:** AI-powered, self-optimising
- **L6-Autonomous:** Self-healing, self-scaling
- **L7-Self-Communicating:** Full bidirectional communication

## Available Tools

The Discovery activity can recommend and use these tools:

### 1. Registry Check (Always Run First)
- **Purpose:** Anti-duplication, prevent duplicate services
- **When:** Always, before any other discovery
- **Action:** Check service catalog for existing services
- **Outcome:** Block if duplicate exists and is healthy

### 2. Discovery Game (7x7)
- **Purpose:** Comprehensive architecture discovery through 49 questions
- **When:** Complex services, new architectures, deep analysis needed
- **Action:** Run 7x7 discovery game across 7 dimensions
- **Outcome:** Comprehensive discovery document

### 3. Design Extraction
- **Purpose:** Infer architecture and technology stack
- **When:** After discovery game or sufficient context
- **Action:** Extract high-level design from discovery artifacts
- **Outcome:** Architecture, tech stack, key components

### 4. Document Generation
- **Purpose:** Create client-facing documents
- **When:** When documents are needed for stakeholders
- **Action:** Generate problem statement and proposed approach docs
- **Outcome:** Professional discovery documents

## Output Structure

```json
{
  "service_name": "mononymic-service-name",
  "problem": {
    "statement": "Clear problem statement",
    "impact": "high|medium|low",
    "root_cause": "Why problem exists",
    "who_has_it": "Stakeholders with the problem"
  },
  "current_state": {
    "what_exists": "Current solutions/systems",
    "pain_points": ["List of pain points"],
    "gaps": ["List of gaps"],
    "blockers": ["List of blockers"]
  },
  "desired_state": {
    "vision": "Vision statement",
    "success_criteria": ["List of success criteria"],
    "goals": ["List of goals"]
  },
  "stakeholders": {
    "users": ["List of users"],
    "decision_makers": ["List of decision makers"],
    "beneficiaries": ["List of beneficiaries"]
  },
  "constraints": {
    "technical": ["Technical constraints"],
    "business": ["Business constraints"],
    "time": "Time constraints",
    "budget": "Budget constraints",
    "compliance": ["Compliance requirements"]
  },
  "requirements": {
    "functional": ["Functional requirements"],
    "non_functional": ["Non-functional requirements"]
  },
  "risks": {
    "technical": ["Technical risks"],
    "business": ["Business risks"],
    "implementation": ["Implementation risks"]
  },
  "alternatives": {
    "other_options": ["Alternative solutions"],
    "why_this_solution": "Rationale for chosen solution"
  },
  "idea": {
    "name": "service-name",
    "type": "service|tool|package|concept",
    "priority": "critical|important|nice-to-have"
  },
  "validation": {
    "problem_solved": true|false,
    "reasoning": "How solution solves problem",
    "confidence": "high|medium|low",
    "assumptions": ["Key assumptions"]
  },
  "recommended_tools": [
    "registry_check",
    "discovery_game",
    "extract_design",
    "generate_documents"
  ],
  "next_steps": "What should happen next in the pipeline"
}
```

## Quality Gates

Discovery must pass these quality gates:

1. **problem_identified:** Problem statement is clear and specific
2. **idea_generated:** Idea/service concept is defined
3. **problem_idea_mapped:** Solution directly addresses the problem
4. **service_name_validated:** Service name meets SPECTRA standards
5. **current_state_understood:** Current state is documented
6. **desired_state_defined:** Desired state is clear
7. **stakeholders_identified:** Key stakeholders are known
8. **constraints_documented:** Constraints are identified
9. **risks_assessed:** Risks are identified and documented
10. **validation_complete:** Solution validation is thorough

## Activity Flow

1. **Registry Check** (automatic, safety)
   - Check if service exists
   - Block if duplicate and healthy
   - Continue if new or unhealthy

2. **Context Loading** (optimized)
   - Load relevant specification (if exists)
   - Load relevant manifest (if exists)
   - Load available tools
   - Load recent history (last 3 entries)
   - **Summarize** context (don't dump full files)

3. **LLM Analysis** (comprehensive)
   - Deep problem understanding
   - Current vs desired state
   - Stakeholder identification
   - Constraint and risk analysis
   - Solution validation
   - Tool recommendations

4. **Tool Execution** (AI-chosen)
   - Execute recommended tools
   - Discovery game (if recommended)
   - Design extraction (if recommended)
   - Document generation (if recommended)

5. **Output Generation** (comprehensive)
   - Generate full discovery output
   - Record quality gates
   - Save manifest
   - Record history

## Success Criteria

Discovery is successful when:

- ✅ Problem is clearly understood and documented
- ✅ Current and desired states are defined
- ✅ Stakeholders, constraints, and risks are identified
- ✅ Solution is validated against the problem
- ✅ Service name meets SPECTRA standards
- ✅ All quality gates pass
- ✅ Next steps are clear

## Integration Points

- **Assess Activity:** Maturity assessment (separate activity)
- **Build Activity:** Uses discovery outputs for architecture decisions
- **Design Activity:** Uses discovery outputs for detailed design
- **Registry:** Checks for duplicates, updates service catalog


