"""
CLI Interface for Orchestrator

Command-line interface for running activities.
"""

import asyncio
import asyncio
import logging
import sys

import click

from .orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(verbose):
    """SPECTRA Orchestrator - AI-agent-based orchestration system."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@main.command()
@click.argument("input_text")
@click.option("--service", "-s", help="Service name")
def discover(input_text, service):
    """Run discovery activity on user input."""
    click.echo(f"Running discovery: {input_text}")
    
    async def run_discover():
        orchestrator = Orchestrator()
        result = await orchestrator.run(
            user_input=input_text,
            activities=["discover"],
            service_name=service,
        )
        
        if result.success:
            discover_result = result.results.get("discover")
            if discover_result:
                click.echo("\nDiscovery Results:")
                click.echo(f"  Service: {discover_result.outputs.get('service_name', 'N/A')}")
                click.echo(f"  Problem: {discover_result.outputs.get('problem', {}).get('statement', 'N/A')}")
                click.echo(f"  Maturity: {discover_result.outputs.get('maturity_assessment', {}).get('level', 'N/A')}")
                click.echo("\n✓ Discovery complete")
        else:
            click.echo(f"\n✗ Discovery failed: {result.errors}", err=True)
            sys.exit(1)
    
    asyncio.run(run_discover())


@main.command()
def status():
    """Check orchestrator status."""
    click.echo("Orchestrator Status:")
    click.echo("  Version: 0.1.0")
    click.echo("  Status: Development")
    
    # Check LLM connection
    async def check_llm():
        from .llm_client import LLMClient
        
        client = LLMClient()
        is_healthy = await client.health_check()
        await client.close()
        
        if is_healthy:
            click.echo("  LLM: Connected")
        else:
            click.echo("  LLM: Not connected")
    
    try:
        asyncio.run(check_llm())
    except Exception as e:
        click.echo(f"  LLM: Error - {e}")


@main.command()
@click.argument("input_text")
@click.option("--activities", "-a", multiple=True, help="Activities to run")
@click.option("--service", "-s", help="Service name")
def run(input_text, activities, service):
    """Run orchestrator with user input."""
    click.echo(f"Running orchestrator: {input_text}")
    
    activity_list = list(activities) if activities else None
    
    async def run_orchestrator():
        orchestrator = Orchestrator()
        result = await orchestrator.run(
            user_input=input_text,
            activities=activity_list,
            service_name=service,
        )
        
        if result.success:
            click.echo(f"\n✓ Orchestration complete")
            click.echo(f"  Activities executed: {', '.join(result.activities_executed)}")
        else:
            click.echo(f"\n✗ Orchestration failed: {result.errors}", err=True)
            sys.exit(1)
    
    asyncio.run(run_orchestrator())


if __name__ == "__main__":
    main()

