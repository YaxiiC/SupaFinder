"""CLI entrypoint for PhD Supervisor Finder."""

from pathlib import Path
from typing import Optional
import typer

from app.config import TARGET_SUPERVISORS, OUTPUTS_DIR
from app.pipeline import run_pipeline

app = typer.Typer(help="PhD Supervisor Finder - AI-assisted supervisor discovery")


@app.command()
def main(
    cv: Optional[Path] = typer.Option(None, "--cv", help="Path to CV file (PDF or text) - optional, but at least one of CV or keywords is required"),
    keywords: Optional[str] = typer.Option(None, "--keywords", help="Research keywords (comma-separated) - optional, but at least one of CV or keywords is required"),
    universities: Path = typer.Option(..., "--universities", help="Path to universities Excel file"),
    out: Path = typer.Option(OUTPUTS_DIR / "supervisors.xlsx", "--out", help="Output Excel file path"),
    regions: Optional[str] = typer.Option(None, "--regions", help="Filter by regions (comma-separated, e.g., 'Europe,North America,Asia')"),
    countries: Optional[str] = typer.Option(None, "--countries", help="Filter by countries (comma-separated, e.g., 'Singapore,Sweden,United Kingdom')"),
    qs_min: Optional[int] = typer.Option(None, "--qs_min", help="Minimum QS rank to include (e.g., 1 for top universities)"),
    qs_max: Optional[int] = typer.Option(None, "--qs_max", help="Maximum QS rank to include (e.g., 50 for top 50)"),
    target: int = typer.Option(TARGET_SUPERVISORS, "--target", help="Target number of supervisors")
):
    """
    Find PhD supervisors based on your CV and/or research interests.
    
    At least one of --cv or --keywords must be provided. Both are optional.
    
    Examples:
        # Basic usage with both CV and keywords
        python -m app.main --cv data/cv.pdf --keywords "machine learning, NLP" --universities data/universities.xlsx
        
        # Using only CV
        python -m app.main --cv data/cv.pdf --universities data/universities.xlsx
        
        # Using only keywords
        python -m app.main --keywords "machine learning, NLP" --universities data/universities.xlsx
        
        # Filter by region
        python -m app.main --cv data/cv.pdf --keywords "AI" --universities data/universities.xlsx --regions "Europe,North America"
        
        # Filter by QS rank range (top 50)
        python -m app.main --keywords "AI" --universities data/universities.xlsx --qs_min 1 --qs_max 50
        
        # Combined filters (top 30 universities in Europe)
        python -m app.main --cv data/cv.pdf --keywords "AI" --universities data/universities.xlsx --regions "Europe" --qs_min 1 --qs_max 30
        
        # Filter by countries
        python -m app.main --cv data/cv.pdf --keywords "AI" --universities data/universities.xlsx --countries "Singapore,Sweden"
    """
    
    # Validate that at least one of CV or keywords is provided
    if not cv and not keywords:
        typer.echo("Error: At least one of --cv or --keywords must be provided", err=True)
        raise typer.Exit(1)
    
    # Parse regions
    regions_list = None
    if regions:
        regions_list = [r.strip() for r in regions.split(",")]
    
    # Parse countries
    countries_list = None
    if countries:
        countries_list = [c.strip() for c in countries.split(",")]
    
    # Validate QS rank range
    if qs_min is not None and qs_max is not None and qs_min > qs_max:
        typer.echo(f"Error: --qs_min ({qs_min}) must be <= --qs_max ({qs_max})", err=True)
        raise typer.Exit(1)
    
    # Run pipeline
    run_pipeline(
        cv_path=cv,
        keywords=keywords,
        universities_path=universities,
        output_path=out,
        regions=regions_list,
        countries=countries_list,
        qs_min=qs_min,
        qs_max=qs_max,
        target=target
    )


if __name__ == "__main__":
    app()

