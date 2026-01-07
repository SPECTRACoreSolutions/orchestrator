"""
Document Generator - Production-ready markdown document generation

Generates client-facing, PDF-ready, GitHub-ready documents with proper formatting.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Generate production-ready markdown documents with frontmatter."""

    @staticmethod
    def generate_frontmatter(
        title: str,
        service: str,
        document_type: str,
        version: str = "1.0",
        **kwargs
    ) -> str:
        """
        Generate YAML frontmatter for markdown documents.

        Args:
            title: Document title
            service: Service name
            document_type: Type of document (problem-statement, discovery-report, etc.)
            version: Document version
            **kwargs: Additional metadata fields

        Returns:
            YAML frontmatter string
        """
        frontmatter = {
            "title": title,
            "service": service,
            "document_type": document_type,
            "version": version,
            "status": "discovery",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "prepared_by": "SPECTRA Orchestrator",
            "classification": "client-facing",
            "ready_for_pdf": True,
            **kwargs,
        }

        lines = ["---"]
        for key, value in frontmatter.items():
            if value is not None:
                if isinstance(value, str) and ("'" in value or '"' in value or ":" in value):
                    lines.append(f'{key}: "{value}"')
                else:
                    lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_problem_statement(discovery_data: Dict[str, Any], service_name: str) -> str:
        """
        Generate Problem Statement document.

        Args:
            discovery_data: Discovery manifest outputs
            service_name: Service name

        Returns:
            Complete markdown document
        """
        problem = discovery_data.get("problem", {})
        current_state = discovery_data.get("current_state", {})
        desired_state = discovery_data.get("desired_state", {})

        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Problem Statement - {service_name.title()} Service",
            service=service_name,
            document_type="problem-statement",
        )

        doc = [frontmatter]
        doc.append(f"# Problem Statement\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")

        # The Problem
        doc.append("## The Problem\n")
        # Check both 'statement' and 'description' fields (LLM may use either)
        problem_stmt = problem.get("statement") or problem.get("description") or "Problem statement to be documented"
        doc.append(problem_stmt)
        doc.append("\n")
        
        # Add who has the problem if available
        if problem.get("who_has_it"):
            doc.append(f"**Who Has This Problem:** {problem.get('who_has_it')}\n\n")

        if problem.get("root_cause"):
            doc.append("### Root Cause\n")
            doc.append(problem.get("root_cause"))
            doc.append("\n")

        doc.append("---\n")

        # Current State
        doc.append("## Current State\n")
        current_desc = current_state.get("description", "[Current state to be documented during discovery]")
        doc.append(current_desc)
        doc.append("\n")

        # Pain Points
        pain_points = current_state.get("pain_points", [])
        if pain_points:
            doc.append("### Pain Points\n")
            for point in pain_points:
                doc.append(f"- {point}")
            doc.append("\n")

        # Gaps
        gaps = current_state.get("gaps", [])
        if gaps:
            doc.append("### Gaps\n")
            for gap in gaps:
                doc.append(f"- {gap}")
            doc.append("\n")

        doc.append("---\n")

        # Impact
        doc.append("## Impact\n")
        impact = problem.get("impact", "medium")
        
        # Handle impact - could be full description or just level
        if isinstance(impact, str):
            # Check if it's a description or just a level
            impact_levels = ["high", "medium", "low"]
            is_level = any(level in impact.lower() for level in impact_levels)
            
            if is_level and len(impact.split()) <= 3:
                # It's just a level
                doc.append(f"**Impact Level:** {impact.title()}\n")
            else:
                # It's a full description
                doc.append(f"**Impact:** {impact}\n")
        else:
            doc.append(f"**Impact Level:** {impact}\n")
        
        doc.append("\n### Impact Details\n")
        doc.append("The current situation has significant impacts across multiple dimensions:\n")
        
        # Parse impact description for key impacts
        impact_text = str(impact).lower()
        impact_details = []
        
        if any(word in impact_text for word in ["time", "mttr", "resolution", "downtime"]):
            impact_details.append("**Time**: Increased mean time to resolution (MTTR) affects system reliability and user experience.")
        if any(word in impact_text for word in ["cost", "expense", "budget", "expensive"]):
            impact_details.append("**Cost**: Additional costs from inefficient troubleshooting and potential service disruptions.")
        if any(word in impact_text for word in ["risk", "security", "vulnerability", "threat"]):
            impact_details.append("**Risk**: Security vulnerabilities and compliance risks from lack of centralized monitoring.")
        if any(word in impact_text for word in ["performance", "efficiency", "slow"]):
            impact_details.append("**Performance**: Degraded system performance affects overall service quality.")
        
        if impact_details:
            for detail in impact_details:
                doc.append(f"- {detail}")
        else:
            # Fallback: extract meaningful impact from description
            if isinstance(impact, str) and len(impact) > 20:
                doc.append(f"- **Overall Impact**: {impact}")
            else:
                doc.append(f"- **Overall Impact**: {impact}")
        doc.append("\n")

        doc.append("---\n")

        # What's Missing - derive from gaps and desired state
        doc.append("## What's Missing\n")
        missing_items = []
        
        # Extract from gaps
        gaps = current_state.get("gaps", [])
        if gaps:
            for gap in gaps:
                missing_items.append(f"A {gap.lower()}")
        else:
            # Derive from desired state if gaps not specified
            goals = desired_state.get("goals", [])
            if goals:
                for goal in goals:
                    missing_items.append(f"Capability for {goal.lower()}")
        
        if missing_items:
            doc.append("The following capabilities are currently missing:\n")
            for item in missing_items:
                doc.append(f"- {item}")
            doc.append("\n")
        else:
            doc.append("Current assessment indicates missing capabilities that would address the identified pain points and gaps.\n\n")
        doc.append("---\n")

        # Desired State (Brief)
        if desired_state.get("vision"):
            doc.append("## Desired State\n")
            doc.append(desired_state.get("vision"))
            doc.append("\n")
            if desired_state.get("success_criteria"):
                doc.append("### Success Criteria\n")
                for criterion in desired_state.get("success_criteria", []):
                    doc.append(f"- {criterion}")
                doc.append("\n")
            doc.append("---\n")

        # Validation
        doc.append("## Validation\n")
        doc.append("This problem statement has been validated through SPECTRA's systematic discovery process:\n")
        doc.append("\n")
        doc.append("- ✅ Problem clearly identified")
        doc.append("- ✅ Current state documented")
        doc.append("- ✅ Pain points understood")
        doc.append("- ✅ Impact assessed")
        doc.append("- ✅ No assumptions or guesswork")
        doc.append("\n")
        doc.append("---\n")

        # Next Steps
        doc.append("**Next Steps:**\n")
        doc.append("\n")
        doc.append("1. Review and confirm this problem statement")
        doc.append("2. Proceed to Strategise stage (define success criteria)")
        doc.append("3. Proceed to Design stage (detailed architecture)")
        doc.append("\n")
        doc.append("---\n")
        doc.append("\n")
        doc.append(
            "_This Problem Statement was generated using SPECTRA's systematic discovery methodology, "
            "ensuring comprehensive understanding of the problem before proposing solutions._\n"
        )
        doc.append("\n")
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")

        return "\n".join(doc)

    @staticmethod
    def generate_discovery_report(discovery_data: Dict[str, Any], service_name: str) -> str:
        """
        Generate Discovery Report (executive summary of all findings).

        Args:
            discovery_data: Discovery manifest outputs
            service_name: Service name

        Returns:
            Complete markdown document
        """
        problem = discovery_data.get("problem", {})
        current_state = discovery_data.get("current_state", {})
        desired_state = discovery_data.get("desired_state", {})
        constraints = discovery_data.get("constraints", {})
        requirements = discovery_data.get("requirements", {})
        risks = discovery_data.get("risks", {})
        alternatives = discovery_data.get("alternatives", {})
        validation = discovery_data.get("validation", {})
        next_steps = discovery_data.get("next_steps", {})

        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Discovery Report - {service_name.title()} Service",
            service=service_name,
            document_type="discovery-report",
        )

        doc = [frontmatter]
        doc.append(f"# Discovery Report\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")

        # Executive Summary
        doc.append("## Executive Summary\n")
        doc.append("This document provides an executive summary of the discovery findings for the ")
        doc.append(f"**{service_name}** service. For detailed analysis, please refer to the individual ")
        doc.append("discovery documents in this portfolio.\n\n")
        doc.append("Discovery explored 10 key dimensions to ensure complete understanding of the problem, ")
        doc.append("context, and solution requirements. This executive summary highlights key findings ")
        doc.append("and recommendations.\n")
        doc.append("\n---\n")

        # Problem Analysis
        doc.append("## Problem Analysis\n")
        
        # Problem Statement/Description
        problem_stmt = problem.get("statement") or problem.get("description")
        if problem_stmt:
            doc.append("### Problem Statement\n")
            doc.append(problem_stmt)
            doc.append("\n")
        
        # Who has the problem
        if problem.get("who_has_it"):
            doc.append(f"**Who Has This Problem:** {problem.get('who_has_it')}\n\n")
        
        # Impact - expanded
        if problem.get("impact"):
            impact = problem.get("impact")
            doc.append("### Impact\n")
            if isinstance(impact, str) and len(impact) > 30:
                doc.append(impact)
                doc.append("\n")
            else:
                doc.append(f"**Impact Level:** {impact.title()}\n")
                doc.append("\nThis problem affects multiple dimensions of the organisation, including operational efficiency, system reliability, and user experience.\n\n")
        
        # Root Cause
        if problem.get("root_cause"):
            doc.append("### Root Cause Analysis\n")
            doc.append(problem.get("root_cause"))
            doc.append("\n")
        
        doc.append("\n---\n")

        # Current State
        doc.append("## Current State Analysis\n")
        if current_state.get("description"):
            doc.append("### Current Situation\n")
            doc.append(current_state.get("description"))
            doc.append("\n")
        
        if current_state.get("pain_points"):
            doc.append("### Pain Points\n")
            doc.append("The following pain points have been identified:\n")
            for point in current_state.get("pain_points", []):
                doc.append(f"- **{point}**: This creates operational inefficiencies and impacts service quality.")
            doc.append("\n")
        
        if current_state.get("gaps"):
            doc.append("### Identified Gaps\n")
            doc.append("Analysis reveals the following capability gaps:\n")
            for gap in current_state.get("gaps", []):
                doc.append(f"- **{gap}**: This gap prevents effective management and monitoring of system operations.")
            doc.append("\n")
        doc.append("---\n")

        # Desired State
        doc.append("## Desired State Vision\n")
        if desired_state.get("vision"):
            doc.append("### Vision Statement\n")
            doc.append(desired_state.get("vision"))
            doc.append("\n")
            doc.append("This vision represents the target state that will address the identified problems and gaps.\n\n")
        
        if desired_state.get("success_criteria"):
            doc.append("### Success Criteria\n")
            doc.append("The solution will be considered successful when the following criteria are met:\n")
            for criterion in desired_state.get("success_criteria", []):
                doc.append(f"- **{criterion}**: Measurable improvement in this area will validate solution effectiveness.")
            doc.append("\n")
        
        if desired_state.get("goals"):
            doc.append("### Strategic Goals\n")
            doc.append("The solution aims to achieve the following strategic goals:\n")
            for goal in desired_state.get("goals", []):
                doc.append(f"- **{goal}**: This capability will directly address identified pain points.")
            doc.append("\n")
        doc.append("---\n")

        # Constraints
        if constraints:
            doc.append("## Constraints\n")
            if constraints.get("technical"):
                doc.append("### Technical Constraints\n")
                tech_constraints = constraints.get("technical", [])
                if isinstance(tech_constraints, list):
                    for constraint in tech_constraints:
                        doc.append(f"- {constraint}")
                else:
                    doc.append(f"- {tech_constraints}")
                doc.append("\n")
            if constraints.get("business"):
                doc.append("### Business Constraints\n")
                biz_constraints = constraints.get("business", [])
                if isinstance(biz_constraints, list):
                    for constraint in biz_constraints:
                        doc.append(f"- {constraint}")
                else:
                    doc.append(f"- {biz_constraints}")
                doc.append("\n")
            if constraints.get("time"):
                doc.append(f"### Time Constraints: {constraints.get('time')}\n")
            if constraints.get("budget"):
                doc.append(f"### Budget Constraints: {constraints.get('budget')}\n")
            doc.append("---\n")

        # Requirements Overview
        if requirements:
            doc.append("## Requirements Overview\n")
            doc.append("Based on the discovery analysis, the following requirements have been identified:\n\n")
            
            if requirements.get("functional"):
                doc.append("### Functional Requirements\n")
                doc.append("The solution must provide the following functional capabilities:\n")
                for req in requirements.get("functional", []):
                    doc.append(f"- **{req}**: Essential functionality required to address the identified needs.")
                doc.append("\n")
            
            if requirements.get("non_functional"):
                doc.append("### Non-Functional Requirements\n")
                doc.append("The solution must meet the following quality attributes:\n")
                for req in requirements.get("non_functional", []):
                    doc.append(f"- **{req}**: Critical quality attribute that ensures solution effectiveness and reliability.")
                doc.append("\n")
            doc.append("---\n")

        # Risk Assessment
        if risks:
            doc.append("## Risk Assessment\n")
            if risks.get("technical"):
                doc.append("### Technical Risks\n")
                tech_risks = risks.get("technical", [])
                if isinstance(tech_risks, list):
                    for risk in tech_risks:
                        doc.append(f"- {risk}")
                else:
                    doc.append(f"- {tech_risks}")
                doc.append("\n")
            if risks.get("business"):
                doc.append("### Business Risks\n")
                biz_risks = risks.get("business", [])
                if isinstance(biz_risks, list):
                    for risk in biz_risks:
                        doc.append(f"- {risk}")
                else:
                    doc.append(f"- {biz_risks}")
                doc.append("\n")
            if risks.get("implementation"):
                doc.append("### Implementation Risks\n")
                impl_risks = risks.get("implementation", [])
                if isinstance(impl_risks, list):
                    for risk in impl_risks:
                        doc.append(f"- {risk}")
                else:
                    doc.append(f"- {impl_risks}")
                doc.append("\n")
            doc.append("---\n")

        # Alternatives
        if alternatives and alternatives.get("options"):
            doc.append("## Alternatives Considered\n")
            for option in alternatives.get("options", []):
                doc.append(f"- {option}")
            doc.append("\n")
            if alternatives.get("why_this_solution"):
                doc.append("### Why This Solution\n")
                doc.append(alternatives.get("why_this_solution"))
                doc.append("\n")
            doc.append("---\n")

        # Validation
        if validation:
            doc.append("## Solution Validation\n")
            if validation.get("solution_solves_problem"):
                doc.append(f"**Solution Solves Problem:** {validation.get('solution_solves_problem')}\n")
            if validation.get("confidence"):
                doc.append(f"**Confidence Level:** {validation.get('confidence').title()}\n")
            if validation.get("assumptions"):
                doc.append("### Assumptions\n")
                for assumption in validation.get("assumptions", []):
                    doc.append(f"- {assumption}")
                doc.append("\n")
            doc.append("---\n")

        # Recommendations & Next Steps
        doc.append("## Recommendations & Next Steps\n")
        if next_steps:
            if isinstance(next_steps, dict):
                for key, value in next_steps.items():
                    doc.append(f"### {key.replace('_', ' ').title()}\n")
                    doc.append(f"{value}\n")
            else:
                doc.append(f"{next_steps}\n")
        else:
            doc.append("1. Proceed to Strategise stage (define business requirements and success criteria)\n")
            doc.append("2. Proceed to Design stage (detailed technical architecture)\n")
        doc.append("\n---\n")

        # Validation Footer
        doc.append("## Validation\n")
        doc.append("This discovery report has been validated through SPECTRA's systematic discovery process:\n")
        doc.append("\n")
        doc.append("- ✅ All 10 discovery dimensions explored")
        doc.append("- ✅ Problem clearly understood")
        doc.append("- ✅ Current and desired state documented")
        doc.append("- ✅ Constraints and risks identified")
        doc.append("- ✅ Solution validated")
        doc.append("\n")
        doc.append("---\n")
        doc.append("\n")
        doc.append(
            "_This Discovery Report was generated using SPECTRA's systematic discovery methodology, "
            "ensuring comprehensive understanding before proceeding to design and implementation._\n"
        )
        doc.append("\n")
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")

        return "\n".join(doc)

    @staticmethod
    def generate_portfolio_index(discovery_data: Dict[str, Any], service_name: str) -> str:
        """
        Generate Discovery Portfolio Index (landing page for discovery documents).

        Args:
            discovery_data: Discovery manifest outputs
            service_name: Service name

        Returns:
            Complete markdown document
        """
        problem = discovery_data.get("problem", {})
        validation = discovery_data.get("validation", {})

        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Discovery Portfolio - {service_name.title()} Service",
            service=service_name,
            document_type="portfolio-index",
        )

        doc = [frontmatter]
        doc.append(f"# Discovery Portfolio\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Status:** Discovery Complete")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")

        # Service Overview
        doc.append("## Service Overview\n")
        doc.append(f"The **{service_name}** service addresses the following problem:\n\n")
        
        # Use description or statement, whichever is available
        problem_text = problem.get("statement") or problem.get("description") or ""
        if problem_text:
            # Use blockquote for problem statement
            doc.append(f"> {problem_text}\n\n")
        
        doc.append("This service has been designed to provide a comprehensive solution that addresses the identified needs and gaps.\n\n")

        # Status
        doc.append("### Discovery Status\n")
        doc.append("- ✅ Problem identified and validated")
        doc.append("- ✅ Current state documented")
        doc.append("- ✅ Desired state defined")
        doc.append("- ✅ Constraints and risks assessed")
        if validation.get("confidence"):
            doc.append(f"- ✅ Solution confidence: {validation.get('confidence').title()}")
        doc.append("\n")

        # Document Links
        doc.append("## Discovery Portfolio Documents\n")
        doc.append("\n")
        doc.append("This comprehensive discovery portfolio contains detailed analysis across all discovery dimensions:\n\n")
        doc.append("### Core Discovery Documents\n\n")
        doc.append("1. **[Problem Statement](01-problem-statement.md)**")
        doc.append("   - Clear articulation of the problem")
        doc.append("   - Root cause analysis")
        doc.append("   - Impact assessment")
        doc.append("\n")
        doc.append("2. **[Current State Analysis](02-current-state-analysis.md)**")
        doc.append("   - Current situation description")
        doc.append("   - Pain points analysis")
        doc.append("   - Capability gaps identification")
        doc.append("\n")
        doc.append("3. **[Desired State Vision](03-desired-state-vision.md)**")
        doc.append("   - Vision statement")
        doc.append("   - Success criteria")
        doc.append("   - Strategic goals")
        doc.append("\n")
        doc.append("4. **[Stakeholder Analysis](04-stakeholder-analysis.md)**")
        doc.append("   - Primary users")
        doc.append("   - Decision makers")
        doc.append("   - Beneficiaries and affected parties")
        doc.append("   - Engagement strategy")
        doc.append("\n")
        doc.append("5. **[Requirements Specification](05-requirements-specification.md)**")
        doc.append("   - Functional requirements")
        doc.append("   - Non-functional requirements")
        doc.append("   - Requirements traceability")
        doc.append("\n")
        doc.append("6. **[Constraints Analysis](06-constraints-analysis.md)**")
        doc.append("   - Technical constraints")
        doc.append("   - Business constraints")
        doc.append("   - Time and budget constraints")
        doc.append("   - Compliance requirements")
        doc.append("\n")
        doc.append("7. **[Risk Assessment](07-risk-assessment.md)**")
        doc.append("   - Technical risks")
        doc.append("   - Business risks")
        doc.append("   - Implementation risks")
        doc.append("   - Risk mitigation strategies")
        doc.append("\n")
        doc.append("8. **[Alternatives Analysis](08-alternatives-analysis.md)**")
        doc.append("   - Alternative solutions considered")
        doc.append("   - Comparison and evaluation")
        doc.append("   - Solution selection rationale")
        doc.append("\n")
        doc.append("9. **[Solution Validation](09-solution-validation.md)**")
        doc.append("   - Solution validation assessment")
        doc.append("   - Confidence level")
        doc.append("   - Key assumptions")
        doc.append("   - Validation criteria")
        doc.append("\n")
        doc.append("10. **[Discovery Report](10-discovery-report.md)**")
        doc.append("    - Executive summary")
        doc.append("    - Key findings overview")
        doc.append("    - Recommendations")
        doc.append("    - Next steps")
        doc.append("\n")

        # Quick Facts
        doc.append("## Quick Facts\n")
        doc.append("\n")
        if problem.get("impact"):
            impact = problem.get("impact")
            # Handle case where impact might be a full description instead of just level
            if isinstance(impact, str) and len(impact) > 20:
                # Extract just the level if it's a long description
                impact_levels = ["high", "medium", "low"]
                for level in impact_levels:
                    if level in impact.lower():
                        impact = level
                        break
            doc.append(f"- **Impact Level:** {impact.title()}")
        if validation.get("confidence"):
            doc.append(f"- **Solution Confidence:** {validation.get('confidence').title()}")
        doc.append(f"- **Service Type:** {discovery_data.get('idea', {}).get('type', 'service')}")
        doc.append(f"- **Priority:** {discovery_data.get('idea', {}).get('priority', 'important')}")
        doc.append("\n")

        # Next Steps
        doc.append("## Next Steps in Pipeline\n")
        doc.append("\n")
        doc.append("1. **Strategise Stage** - Define business requirements and success criteria")
        doc.append("2. **Design Stage** - Create detailed technical architecture")
        doc.append("3. **Build Stage** - Implement the solution")
        doc.append("\n")

        # Usage
        doc.append("## Using This Portfolio\n")
        doc.append("\n")
        doc.append("This portfolio is ready for:")
        doc.append("- 📄 PDF generation for client review")
        doc.append("- 🔗 GitHub README integration")
        doc.append("- 📊 Service catalog presentation")
        doc.append("\n")

        doc.append("---\n")
        doc.append("\n")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        doc.append("**Generated by:** SPECTRA Orchestrator")

        return "\n".join(doc)

    @staticmethod
    def generate_current_state_analysis(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Current State Analysis document."""
        current_state = discovery_data.get("current_state", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Current State Analysis - {service_name.title()} Service",
            service=service_name,
            document_type="current-state-analysis",
        )
        
        doc = [frontmatter]
        doc.append(f"# Current State Analysis\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        # Current Situation
        if current_state.get("description"):
            doc.append("## Current Situation\n")
            doc.append(current_state.get("description"))
            doc.append("\n\n")
        
        # Pain Points
        pain_points = current_state.get("pain_points", [])
        if pain_points:
            doc.append("## Pain Points\n")
            doc.append("The following operational pain points have been identified:\n\n")
            for i, point in enumerate(pain_points, 1):
                doc.append(f"### {i}. {point}\n")
                doc.append(f"This issue creates operational inefficiencies and impacts service quality, user experience, and system reliability.\n\n")
            doc.append("---\n")
        
        # Gaps
        gaps = current_state.get("gaps", [])
        if gaps:
            doc.append("## Identified Capability Gaps\n")
            doc.append("Analysis reveals the following critical gaps in current capabilities:\n\n")
            for i, gap in enumerate(gaps, 1):
                doc.append(f"### {i}. {gap}\n")
                doc.append(f"This gap prevents effective management, monitoring, and optimization of system operations.\n\n")
            doc.append("---\n")
        
        # Impact of Current State
        doc.append("## Impact of Current State\n")
        doc.append("The fragmented and inconsistent current state creates significant impacts:\n\n")
        doc.append("- **Operational Efficiency**: Inefficient processes and workflows\n")
        doc.append("- **System Reliability**: Inconsistent monitoring and response capabilities\n")
        doc.append("- **User Experience**: Reduced service quality and availability\n")
        doc.append("- **Strategic Alignment**: Gaps prevent achieving business objectives\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_desired_state_vision(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Desired State Vision document."""
        desired_state = discovery_data.get("desired_state", {})
        problem = discovery_data.get("problem", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Desired State Vision - {service_name.title()} Service",
            service=service_name,
            document_type="desired-state-vision",
        )
        
        doc = [frontmatter]
        doc.append(f"# Desired State Vision\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        # Vision Statement
        if desired_state.get("vision"):
            doc.append("## Vision Statement\n")
            doc.append(desired_state.get("vision"))
            doc.append("\n\n")
            doc.append("This vision represents the target state that will address the identified problems, close capability gaps, and deliver measurable business value.\n\n")
            doc.append("---\n")
        
        # Success Criteria
        success_criteria = desired_state.get("success_criteria", [])
        if success_criteria:
            doc.append("## Success Criteria\n")
            doc.append("The solution will be considered successful when the following measurable criteria are met:\n\n")
            for i, criterion in enumerate(success_criteria, 1):
                doc.append(f"### {i}. {criterion}\n")
                doc.append(f"Measurable improvement in this area will validate solution effectiveness and demonstrate return on investment.\n\n")
            doc.append("---\n")
        
        # Strategic Goals
        goals = desired_state.get("goals", [])
        if goals:
            doc.append("## Strategic Goals\n")
            doc.append("The solution aims to achieve the following strategic goals:\n\n")
            for i, goal in enumerate(goals, 1):
                doc.append(f"### {i}. {goal}\n")
                doc.append(f"This capability will directly address identified pain points and enable new opportunities.\n\n")
            doc.append("---\n")
        
        # Target Outcomes
        doc.append("## Target Outcomes\n")
        doc.append("Achieving the desired state will deliver the following outcomes:\n\n")
        if problem.get("impact"):
            doc.append("- **Problem Resolution**: Addresses the core problem: ")
            doc.append(f"{problem.get('impact', 'identified challenges')}\n")
        doc.append("- **Operational Excellence**: Streamlined processes and improved efficiency\n")
        doc.append("- **Business Value**: Measurable improvements in key performance indicators\n")
        doc.append("- **Strategic Alignment**: Enables achievement of business objectives\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_stakeholder_analysis(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Stakeholder Analysis document."""
        stakeholders = discovery_data.get("stakeholders", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Stakeholder Analysis - {service_name.title()} Service",
            service=service_name,
            document_type="stakeholder-analysis",
        )
        
        doc = [frontmatter]
        doc.append(f"# Stakeholder Analysis\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document identifies all parties affected by or involved in the solution, their roles, interests, and expectations.\n\n")
        doc.append("---\n")
        
        # Primary Users
        users = stakeholders.get("users")
        if users:
            doc.append("## Primary Users\n")
            doc.append("These are the individuals or teams who will directly interact with and use the solution:\n\n")
            if isinstance(users, list):
                for user in users:
                    doc.append(f"- **{user}**: Will directly interact with and benefit from the solution on a daily basis.\n")
            else:
                doc.append(f"- **{users}**: Will directly interact with and benefit from the solution on a daily basis.\n")
            doc.append("\n**User Needs**: Efficient, intuitive interface; reliable performance; comprehensive functionality\n\n")
            doc.append("---\n")
        
        # Decision Makers
        decision_makers = stakeholders.get("decision_makers")
        if decision_makers:
            doc.append("## Decision Makers\n")
            doc.append("These are the individuals or groups responsible for approving, funding, and championing the solution:\n\n")
            if isinstance(decision_makers, list):
                for dm in decision_makers:
                    doc.append(f"- **{dm}**: Responsible for approving and funding the solution, ensuring alignment with business strategy.\n")
            else:
                doc.append(f"- **{decision_makers}**: Responsible for approving and funding the solution, ensuring alignment with business strategy.\n")
            doc.append("\n**Decision Maker Needs**: Clear business case; ROI demonstration; risk mitigation; strategic alignment\n\n")
            doc.append("---\n")
        
        # Beneficiaries
        beneficiaries = stakeholders.get("beneficiaries")
        if beneficiaries:
            doc.append("## Beneficiaries\n")
            doc.append("These are the parties who will experience improved outcomes as a result of the solution:\n\n")
            if isinstance(beneficiaries, list):
                for beneficiary in beneficiaries:
                    doc.append(f"- **{beneficiary}**: Will experience improved outcomes, enhanced service quality, and better overall experience.\n")
            else:
                doc.append(f"- **{beneficiaries}**: Will experience improved outcomes, enhanced service quality, and better overall experience.\n")
            doc.append("\n**Beneficiary Needs**: Improved service quality; better reliability; enhanced experience\n\n")
            doc.append("---\n")
        
        # Affected Parties
        affected = stakeholders.get("affected_parties")
        if affected:
            doc.append("## Affected Parties\n")
            doc.append("These are the parties who will be impacted by the implementation and should be considered in planning:\n\n")
            if isinstance(affected, list):
                for party in affected:
                    doc.append(f"- **{party}**: Will be impacted by implementation and should be consulted, informed, and prepared for changes.\n")
            else:
                doc.append(f"- **{affected}**: Will be impacted by implementation and should be consulted, informed, and prepared for changes.\n")
            doc.append("\n**Affected Party Needs**: Clear communication; change management; training and support\n\n")
            doc.append("---\n")
        
        # Stakeholder Engagement Strategy
        doc.append("## Stakeholder Engagement Strategy\n")
        doc.append("### Engagement Approach\n\n")
        doc.append("- **Primary Users**: Involve in requirements gathering, user acceptance testing, and feedback sessions\n")
        doc.append("- **Decision Makers**: Provide regular updates, business case reviews, and decision points\n")
        doc.append("- **Beneficiaries**: Communicate benefits, gather expectations, and measure satisfaction\n")
        doc.append("- **Affected Parties**: Inform early, manage change, provide training and support\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_requirements_specification(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Requirements Specification document."""
        requirements = discovery_data.get("requirements", {})
        desired_state = discovery_data.get("desired_state", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Requirements Specification - {service_name.title()} Service",
            service=service_name,
            document_type="requirements-specification",
        )
        
        doc = [frontmatter]
        doc.append(f"# Requirements Specification\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document specifies the functional and non-functional requirements for the solution, derived from discovery analysis and stakeholder needs.\n\n")
        doc.append("---\n")
        
        # Functional Requirements
        functional = requirements.get("functional", [])
        if functional:
            doc.append("## Functional Requirements\n")
            doc.append("Functional requirements define what the solution must do - the capabilities and features it must provide:\n\n")
            for i, req in enumerate(functional, 1):
                doc.append(f"### REQ-F{i}: {req}\n")
                doc.append(f"**Description**: The solution must provide {req.lower()} capability.\n")
                doc.append(f"**Rationale**: Essential functionality required to address identified needs and achieve desired state.\n")
                doc.append(f"**Priority**: High\n\n")
            doc.append("---\n")
        
        # Non-Functional Requirements
        non_functional = requirements.get("non_functional", [])
        if non_functional:
            doc.append("## Non-Functional Requirements\n")
            doc.append("Non-functional requirements define how well the solution must perform - quality attributes and constraints:\n\n")
            for i, req in enumerate(non_functional, 1):
                doc.append(f"### REQ-NF{i}: {req}\n")
                doc.append(f"**Description**: The solution must meet {req.lower()} quality standards.\n")
                doc.append(f"**Rationale**: Critical quality attribute that ensures solution effectiveness, reliability, and maintainability.\n")
                doc.append(f"**Priority**: High\n\n")
            doc.append("---\n")
        
        # Requirements Traceability
        doc.append("## Requirements Traceability\n")
        doc.append("### Source Mapping\n\n")
        doc.append("Requirements are derived from:\n")
        doc.append("- **Problem Analysis**: Addressing identified pain points and gaps\n")
        doc.append("- **Desired State**: Enabling achievement of strategic goals and success criteria\n")
        doc.append("- **Stakeholder Needs**: Meeting expectations of users, decision makers, and beneficiaries\n")
        doc.append("- **Constraints**: Operating within technical, business, and compliance boundaries\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_constraints_analysis(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Constraints Analysis document."""
        constraints = discovery_data.get("constraints", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Constraints Analysis - {service_name.title()} Service",
            service=service_name,
            document_type="constraints-analysis",
        )
        
        doc = [frontmatter]
        doc.append(f"# Constraints Analysis\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document identifies all constraints that must be considered and accommodated in the solution design and implementation.\n\n")
        doc.append("---\n")
        
        # Technical Constraints
        technical = constraints.get("technical")
        if technical:
            doc.append("## Technical Constraints\n")
            doc.append("Technical constraints define limitations imposed by technology, infrastructure, or system architecture:\n\n")
            if isinstance(technical, list):
                for constraint in technical:
                    doc.append(f"- **{constraint}**: Must be considered in technical design and implementation.\n")
            else:
                doc.append(f"- **{technical}**: Must be considered in technical design and implementation.\n")
            doc.append("\n**Impact**: Influences technology selection, architecture decisions, and implementation approach\n\n")
            doc.append("---\n")
        
        # Business Constraints
        business = constraints.get("business")
        if business:
            doc.append("## Business Constraints\n")
            doc.append("Business constraints define limitations imposed by organisational policies, processes, or strategic considerations:\n\n")
            if isinstance(business, list):
                for constraint in business:
                    doc.append(f"- **{constraint}**: Must align with business policies and strategic objectives.\n")
            else:
                doc.append(f"- **{business}**: Must align with business policies and strategic objectives.\n")
            doc.append("\n**Impact**: Influences scope, priorities, and resource allocation\n\n")
            doc.append("---\n")
        
        # Time Constraints
        time = constraints.get("time")
        if time:
            doc.append("## Time Constraints\n")
            doc.append(f"**Timeline**: {time}\n\n")
            doc.append("This timeline constraint affects project planning, resource allocation, and delivery approach.\n\n")
            doc.append("**Implications**:\n")
            doc.append("- Influences scope and feature prioritisation\n")
            doc.append("- May require phased delivery approach\n")
            doc.append("- Affects resource and team planning\n\n")
            doc.append("---\n")
        
        # Budget Constraints
        budget = constraints.get("budget")
        if budget:
            doc.append("## Budget Constraints\n")
            doc.append(f"**Budget**: {budget}\n\n")
            doc.append("This budget constraint affects technology choices, resource allocation, and implementation approach.\n\n")
            doc.append("**Implications**:\n")
            doc.append("- Influences technology and vendor selection\n")
            doc.append("- May require cost optimisation strategies\n")
            doc.append("- Affects scope and feature prioritisation\n\n")
            doc.append("---\n")
        
        # Compliance Constraints
        compliance = constraints.get("compliance")
        if compliance:
            doc.append("## Compliance & Regulatory Constraints\n")
            doc.append("Compliance constraints define legal, regulatory, or policy requirements that must be met:\n\n")
            if isinstance(compliance, list):
                for comp in compliance:
                    doc.append(f"- **{comp}**: Must be adhered to throughout design and implementation.\n")
            else:
                doc.append(f"- **{compliance}**: Must be adhered to throughout design and implementation.\n")
            doc.append("\n**Impact**: Influences architecture, data handling, security measures, and implementation approach\n\n")
            doc.append("---\n")
        
        # Constraint Management
        doc.append("## Constraint Management Strategy\n")
        doc.append("### Approach\n\n")
        doc.append("1. **Identify Early**: All constraints documented during discovery\n")
        doc.append("2. **Design Within**: Solution designed to work within constraints\n")
        doc.append("3. **Monitor Changes**: Constraints reviewed and updated as project progresses\n")
        doc.append("4. **Mitigate Impact**: Strategies developed to minimise negative impacts\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_risk_assessment(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Risk Assessment document."""
        risks = discovery_data.get("risks", {})
        constraints = discovery_data.get("constraints", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Risk Assessment - {service_name.title()} Service",
            service=service_name,
            document_type="risk-assessment",
        )
        
        doc = [frontmatter]
        doc.append(f"# Risk Assessment\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document identifies and assesses risks associated with the solution, including likelihood, impact, and mitigation strategies.\n\n")
        doc.append("---\n")
        
        # Technical Risks
        technical_risks = risks.get("technical", [])
        if technical_risks:
            doc.append("## Technical Risks\n")
            doc.append("Technical risks relate to technology, architecture, integration, or implementation challenges:\n\n")
            if isinstance(technical_risks, list):
                for i, risk in enumerate(technical_risks, 1):
                    doc.append(f"### RISK-T{i}: {risk}\n")
                    doc.append(f"**Description**: {risk}\n")
                    doc.append(f"**Likelihood**: Medium\n")
                    doc.append(f"**Impact**: High\n")
                    doc.append(f"**Mitigation**: Technical risk mitigation strategies should be developed during design phase, including proof-of-concept validation, architecture reviews, and incremental implementation.\n\n")
            else:
                doc.append(f"### RISK-T1: {technical_risks}\n")
                doc.append(f"**Description**: {technical_risks}\n")
                doc.append(f"**Likelihood**: Medium\n")
                doc.append(f"**Impact**: High\n")
                doc.append(f"**Mitigation**: Technical risk mitigation strategies should be developed during design phase.\n\n")
            doc.append("---\n")
        
        # Business Risks
        business_risks = risks.get("business", [])
        if business_risks:
            doc.append("## Business Risks\n")
            doc.append("Business risks relate to budget, timeline, resources, or business impact:\n\n")
            if isinstance(business_risks, list):
                for i, risk in enumerate(business_risks, 1):
                    doc.append(f"### RISK-B{i}: {risk}\n")
                    doc.append(f"**Description**: {risk}\n")
                    doc.append(f"**Likelihood**: Medium\n")
                    doc.append(f"**Impact**: High\n")
                    doc.append(f"**Mitigation**: Business risk mitigation strategies should include careful budget management, timeline monitoring, stakeholder communication, and contingency planning.\n\n")
            else:
                doc.append(f"### RISK-B1: {business_risks}\n")
                doc.append(f"**Description**: {business_risks}\n")
                doc.append(f"**Likelihood**: Medium\n")
                doc.append(f"**Impact**: High\n")
                doc.append(f"**Mitigation**: Business risk mitigation strategies should be developed.\n\n")
            doc.append("---\n")
        
        # Implementation Risks
        implementation_risks = risks.get("implementation", [])
        if implementation_risks:
            doc.append("## Implementation Risks\n")
            doc.append("Implementation risks relate to execution, deployment, change management, or operational transition:\n\n")
            if isinstance(implementation_risks, list):
                for i, risk in enumerate(implementation_risks, 1):
                    doc.append(f"### RISK-I{i}: {risk}\n")
                    doc.append(f"**Description**: {risk}\n")
                    doc.append(f"**Likelihood**: Medium\n")
                    doc.append(f"**Impact**: Medium\n")
                    doc.append(f"**Mitigation**: Implementation risk mitigation should include phased rollout, comprehensive testing, change management, and training programmes.\n\n")
            else:
                doc.append(f"### RISK-I1: {implementation_risks}\n")
                doc.append(f"**Description**: {implementation_risks}\n")
                doc.append(f"**Likelihood**: Medium\n")
                doc.append(f"**Impact**: Medium\n")
                doc.append(f"**Mitigation**: Implementation risk mitigation strategies should be developed.\n\n")
            doc.append("---\n")
        
        # Risk Management Strategy
        doc.append("## Risk Management Strategy\n")
        doc.append("### Approach\n\n")
        doc.append("1. **Identify**: Risks identified during discovery phase\n")
        doc.append("2. **Assess**: Likelihood and impact evaluated\n")
        doc.append("3. **Mitigate**: Strategies developed to reduce likelihood or impact\n")
        doc.append("4. **Monitor**: Risks tracked and reviewed throughout project lifecycle\n")
        doc.append("5. **Respond**: Contingency plans ready for high-priority risks\n\n")
        doc.append("---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_alternatives_analysis(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Alternatives Analysis document."""
        alternatives = discovery_data.get("alternatives", {})
        problem = discovery_data.get("problem", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Alternatives Analysis - {service_name.title()} Service",
            service=service_name,
            document_type="alternatives-analysis",
        )
        
        doc = [frontmatter]
        doc.append(f"# Alternatives Analysis\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document evaluates alternative approaches to solving the identified problem and justifies the selected solution.\n\n")
        doc.append("---\n")
        
        # Alternative Options
        options = alternatives.get("options") or alternatives.get("other_options", [])
        if options:
            doc.append("## Alternative Solutions Considered\n\n")
            for i, option in enumerate(options, 1):
                doc.append(f"### Alternative {i}: {option}\n")
                doc.append(f"**Description**: {option}\n\n")
                doc.append("**Pros**:\n")
                doc.append("- Potential benefits of this approach\n\n")
                doc.append("**Cons**:\n")
                doc.append("- Limitations and challenges of this approach\n\n")
                doc.append("**Suitability**: Assessed against requirements, constraints, and strategic objectives\n\n")
            doc.append("---\n")
        
        # Why This Solution
        why_this = alternatives.get("why_this_solution")
        if why_this:
            doc.append("## Why This Solution Was Selected\n")
            doc.append(why_this)
            doc.append("\n\n")
            doc.append("### Decision Factors\n\n")
            doc.append("- **Alignment with Requirements**: Best matches functional and non-functional requirements\n")
            doc.append("- **Constraint Compliance**: Works within identified technical, business, and compliance constraints\n")
            doc.append("- **Strategic Fit**: Aligns with business strategy and objectives\n")
            doc.append("- **Risk Profile**: Acceptable risk level with manageable mitigation strategies\n")
            doc.append("- **Value Delivery**: Provides best balance of benefits, costs, and risks\n\n")
            doc.append("---\n")
        else:
            # Generate default why this solution
            doc.append("## Why This Solution Was Selected\n")
            if problem.get("description"):
                doc.append(f"The proposed solution was selected as it directly addresses the core problem: {problem.get('description')}")
            doc.append("\n\n")
            doc.append("The selected approach offers:\n")
            doc.append("- Best alignment with requirements and constraints\n")
            doc.append("- Optimal balance of benefits, costs, and risks\n")
            doc.append("- Strong strategic fit with business objectives\n")
            doc.append("- Manageable implementation complexity\n\n")
            doc.append("---\n")
        
        # Comparison Summary
        doc.append("## Comparison Summary\n")
        doc.append("| Criteria | Selected Solution | Alternative Options |\n")
        doc.append("|----------|-------------------|---------------------|\n")
        doc.append("| **Requirements Fit** | Best match | Partial match |\n")
        doc.append("| **Constraint Compliance** | Compliant | May have constraints |\n")
        doc.append("| **Risk Level** | Manageable | Higher risk |\n")
        doc.append("| **Value Delivery** | Optimal | Suboptimal |\n")
        doc.append("\n---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

    @staticmethod
    def generate_solution_validation(discovery_data: Dict[str, Any], service_name: str) -> str:
        """Generate Solution Validation document."""
        validation = discovery_data.get("validation", {})
        problem = discovery_data.get("problem", {})
        desired_state = discovery_data.get("desired_state", {})
        
        frontmatter = DocumentGenerator.generate_frontmatter(
            title=f"Solution Validation - {service_name.title()} Service",
            service=service_name,
            document_type="solution-validation",
        )
        
        doc = [frontmatter]
        doc.append(f"# Solution Validation\n")
        doc.append(f"**Service:** {service_name}")
        doc.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n")
        doc.append("---\n")
        
        doc.append("## Overview\n")
        doc.append("This document validates that the proposed solution effectively addresses the identified problem and enables achievement of the desired state.\n\n")
        doc.append("---\n")
        
        # Solution Solves Problem
        solves_problem = validation.get("solution_solves_problem") or validation.get("does_solution_solve_problem")
        if solves_problem:
            doc.append("## Solution Addresses Problem\n")
            if isinstance(solves_problem, bool):
                doc.append(f"**Validation Result**: {'Yes' if solves_problem else 'No'}\n\n")
            else:
                doc.append(f"**Validation**: {solves_problem}\n\n")
            
            if problem.get("description"):
                doc.append("The proposed solution directly addresses the core problem:\n\n")
                doc.append(f"> {problem.get('description')}\n\n")
            
            doc.append("**How Solution Solves Problem**:\n")
            doc.append("- Addresses root causes identified in problem analysis\n")
            doc.append("- Closes capability gaps in current state\n")
            doc.append("- Enables achievement of desired state vision\n")
            doc.append("- Meets functional and non-functional requirements\n\n")
            doc.append("---\n")
        
        # Confidence Level
        confidence = validation.get("confidence")
        if confidence:
            doc.append("## Confidence Assessment\n")
            doc.append(f"**Confidence Level**: {confidence.title()}\n\n")
            doc.append(f"Based on comprehensive discovery analysis, we have {confidence.lower()} confidence that:\n")
            doc.append("- The solution effectively addresses the identified problem\n")
            doc.append("- Requirements can be met within identified constraints\n")
            doc.append("- Risks are manageable with appropriate mitigation\n")
            doc.append("- Desired state can be achieved with this approach\n\n")
            doc.append("---\n")
        
        # Assumptions
        assumptions = validation.get("assumptions", [])
        if assumptions:
            doc.append("## Key Assumptions\n")
            doc.append("The following assumptions underlie this validation:\n\n")
            for i, assumption in enumerate(assumptions, 1):
                doc.append(f"{i}. **{assumption}**\n")
                doc.append("   This assumption should be validated during design and implementation phases.\n\n")
            doc.append("**Assumption Management**:\n")
            doc.append("- Assumptions will be validated during design phase\n")
            doc.append("- Risks associated with assumptions will be monitored\n")
            doc.append("- Contingency plans will be developed for critical assumptions\n\n")
            doc.append("---\n")
        
        # Validation Criteria
        doc.append("## Validation Criteria\n")
        doc.append("The solution will be considered validated when:\n\n")
        if desired_state.get("success_criteria"):
            for criterion in desired_state.get("success_criteria", []):
                doc.append(f"- ✅ {criterion}\n")
        else:
            doc.append("- ✅ All functional requirements are met\n")
            doc.append("- ✅ All non-functional requirements are satisfied\n")
            doc.append("- ✅ Success criteria are achieved\n")
            doc.append("- ✅ Problem is resolved or significantly mitigated\n\n")
        doc.append("\n---\n")
        
        doc.append(f"**Document Version:** 1.0")
        doc.append(f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        return "\n".join(doc)

