"""CLI entrypoint for the Agent War Room pipeline."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="agent-war-room",
    help="Multi-agent job application assistant with live trace dashboard.",
)


@app.command()
def analyze(
    job: Path = typer.Option(..., help="Path to job description file"),
    resume: Path = typer.Option(..., help="Path to resume file (markdown)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use fixture responses instead of API calls"),
) -> None:
    """Analyze a job posting against your resume using 5 AI agents."""
    if not job.exists():
        typer.echo(f"Error: Job file not found: {job}", err=True)
        raise typer.Exit(1)
    if not resume.exists():
        typer.echo(f"Error: Resume file not found: {resume}", err=True)
        raise typer.Exit(1)

    job_text = job.read_text(encoding="utf-8")
    resume_text = resume.read_text(encoding="utf-8")

    if dry_run:
        typer.echo("Dry run mode: using fixture responses (not implemented yet)")
        raise typer.Exit(0)

    typer.echo("Starting Agent War Room pipeline...")
    typer.echo(f"Job: {job}")
    typer.echo(f"Resume: {resume}")
    typer.echo()

    result = asyncio.run(_run_analysis(job_text, resume_text))

    if result is None:
        raise typer.Exit(1)


async def _run_analysis(job_text: str, resume_text: str) -> object:
    """Run the pipeline and print results."""
    from src.orchestrator import run_pipeline
    from src.tracer import Tracer

    tracer = Tracer()

    try:
        package = await run_pipeline(job_text, resume_text, tracer)
    except Exception as e:
        typer.echo(f"\nPipeline error: {e}", err=True)
        tracer.print_trace()
        return None

    # Print trace
    typer.echo("=" * 60)
    typer.echo("EXECUTION TRACE")
    typer.echo("=" * 60)
    tracer.print_trace()

    # Print match report
    typer.echo()
    typer.echo("=" * 60)
    typer.echo("MATCH REPORT")
    typer.echo("=" * 60)
    report = package.match_report
    typer.echo(f"Overall Score: {report.overall_score:.0%}")
    typer.echo(f"Recommendation: {report.recommendation}")

    if report.matched_skills:
        typer.echo("\nMatched Skills:")
        for m in report.matched_skills:
            typer.echo(f"  + {m.skill.name} ({m.confidence:.0%}) -- {m.evidence[:80]}")

    if report.gaps:
        typer.echo("\nGaps:")
        for g in report.gaps:
            transferable = f" (transferable: {g.transferable})" if g.transferable else ""
            typer.echo(f"  - [{g.severity}] {g.skill.name}{transferable}")

    if report.challenges:
        typer.echo("\nDevil's Advocate Challenges:")
        for c in report.challenges:
            typer.echo(f"  ! [{c.severity}] {c.claim}")
            typer.echo(f"    {c.argument}")

    # Print strategy
    typer.echo()
    typer.echo("=" * 60)
    typer.echo("APPLICATION STRATEGY")
    typer.echo("=" * 60)
    typer.echo(package.application_strategy)

    # Print cover letter
    if package.cover_letter:
        typer.echo()
        typer.echo("=" * 60)
        typer.echo("COVER LETTER")
        typer.echo("=" * 60)
        typer.echo(package.cover_letter.text)

    return package


@app.command()
def dashboard() -> None:
    """Launch the live trace dashboard (Weekend 2)."""
    typer.echo("Dashboard not implemented yet. Coming in Weekend 2.")
    typer.echo("Run 'analyze' command to see CLI trace output.")
    raise typer.Exit(0)


@app.command()
def trace() -> None:
    """View the last execution trace (Weekend 2)."""
    typer.echo("Trace viewer not implemented yet. Coming in Weekend 2.")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
