"""CLI commands for Substack Scraper."""

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from ..config import settings
from ..scraper.browser import BrowserManager
from ..scraper.data_extractor import DataExtractor
from ..scraper.post_fetcher import PostFetcher
from ..scraper.scroll_handler import ScrollHandler
from ..scraper.search_scraper import SearchScraper
from ..storage.json_writer import JsonWriter
from ..utils.logging import setup_logging
from ..utils.rate_limiter import RateLimiter

app = typer.Typer(
    name="substack-scraper",
    help="Scrape Substack posts by keyword search",
    add_completion=False,
)
console = Console()


@app.command()
def search(
    keywords: Annotated[
        list[str],
        typer.Argument(help="Keywords to search for"),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum results per keyword"),
    ] = 50,
    output_dir: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output directory for JSON files"),
    ] = None,
    headless: Annotated[
        bool,
        typer.Option("--headless/--no-headless", help="Run browser in headless mode"),
    ] = True,
    fetch_content: Annotated[
        bool,
        typer.Option("--content/--no-content", help="Fetch full post content"),
    ] = True,
    combine: Annotated[
        bool,
        typer.Option("--combine/--no-combine", help="Combine all results into one file"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
) -> None:
    """Search Substack for posts matching keywords."""
    # Setup logging
    log_level = "DEBUG" if verbose else settings.log_level
    setup_logging(log_level)

    # Run async search
    asyncio.run(
        _search_async(
            keywords=keywords,
            limit=limit,
            output_dir=output_dir or settings.output_dir,
            headless=headless,
            fetch_content=fetch_content,
            combine=combine,
        )
    )


async def _search_async(
    keywords: list[str],
    limit: int,
    output_dir: str,
    headless: bool,
    fetch_content: bool,
    combine: bool,
) -> None:
    """Async implementation of search command."""
    console.print(f"\n[bold blue]Substack Post Scraper[/bold blue]")
    console.print(f"Keywords: {', '.join(keywords)}")
    console.print(f"Limit: {limit} posts per keyword")
    console.print(f"Full content: {'Yes' if fetch_content else 'No'}")
    console.print()

    # Initialize components
    browser = BrowserManager(headless=headless)
    scroll_handler = ScrollHandler(
        scroll_delay_ms=settings.scroll_delay_ms,
        timeout_ms=settings.scroll_timeout_ms,
    )
    data_extractor = DataExtractor()
    rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    writer = JsonWriter(output_dir)

    try:
        await browser.start()

        post_fetcher = PostFetcher(browser)
        scraper = SearchScraper(
            browser_manager=browser,
            scroll_handler=scroll_handler,
            data_extractor=data_extractor,
            post_fetcher=post_fetcher,
            rate_limiter=rate_limiter,
            fetch_full_content=fetch_content,
        )

        all_results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            main_task = progress.add_task(
                "[cyan]Searching...",
                total=len(keywords),
            )

            for keyword in keywords:
                progress.update(
                    main_task,
                    description=f"[cyan]Searching: {keyword}",
                )

                try:
                    result = await scraper.search(
                        keyword=keyword,
                        limit=limit,
                        fetch_content=fetch_content,
                    )
                    all_results.append(result)

                    # Save individual result
                    if not combine:
                        filepath = writer.write_search_result_sync(result)
                        console.print(f"  [green]Saved:[/green] {filepath}")

                    # Display summary table
                    table = Table(title=f"Results for '{keyword}'", show_header=True)
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    table.add_row("Posts Found", str(result.total_results))
                    table.add_row("Duration", f"{result.duration_seconds:.2f}s")
                    console.print(table)
                    console.print()

                except Exception as e:
                    console.print(f"  [red]Error:[/red] {str(e)}")

                progress.update(main_task, advance=1)

        # Combine results if requested
        if combine and all_results:
            filepath = writer.write_all_posts_combined(all_results)
            console.print(f"\n[green]Combined results saved to:[/green] {filepath}")

        # Final summary
        total_posts = sum(r.total_results for r in all_results)
        console.print(f"\n[bold green]Complete![/bold green]")
        console.print(f"Total posts scraped: {total_posts}")

    finally:
        await browser.stop()


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="API host"),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="API port"),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", "-r", help="Enable auto-reload"),
    ] = False,
) -> None:
    """Start the FastAPI server."""
    import uvicorn

    console.print(f"\n[bold blue]Starting Substack Scraper API[/bold blue]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Docs: http://{host}:{port}/docs")
    console.print()

    uvicorn.run(
        "substack_scraper.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@app.command()
def version() -> None:
    """Show version information."""
    from .. import __version__

    console.print(f"Substack Scraper v{__version__}")


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
