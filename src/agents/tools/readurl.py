import os
import asyncio
from typing import Optional
from smolagents import Tool
from ..core.scraping.scraper import JinaReaderScraper
from ..core.scraping.result import ExtractionResult


class ReadURLTool(Tool):
    """
    Reads the content of a given URL using Jina Reader API and returns
    the processed content, typically in Markdown format.
    """
    name = "read_url"
    description = (
        "Reads the content of a given URL using Jina Reader API and returns "
        "the processed content, typically in Markdown format."
    )
    inputs = {
        "url": {
            "type": "string",
            "description": "The URL to read content from.",
        },
        "output_format": {
            "type": "string",
            "description": "Desired output format (e.g., 'markdown', 'text').",
            "default": "markdown",
            "nullable": True,
        }
    }
    output_type = "string"  # returns the processed content

    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        reader_model: str = "readerlm-v2",
        cli_console=None,
        verbose: bool = False  # for logging (optional)
    ):
        """
        Initialize ReadURLTool.

        Args:
            jina_api_key (str, optional): Jina AI API key. If None, load from
                environment variable JINA_API_KEY.
            reader_model (str): The Jina Reader model to use.
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        if not self.jina_api_key:
            raise ValueError(
                "JINA_API_KEY is required but not provided "
                "or found in environment."
            )

        self.reader_model = reader_model
        # JinaReaderScraper instance will be created when needed
        # or setup()
        self.scraper: Optional[JinaReaderScraper] = None
        self.cli_console = cli_console
        self.verbose = verbose

    def _ensure_scraper(self, output_format: str = "markdown"):
        """Ensure JinaReaderScraper instance is created and
        configured correctly."""
        if self.scraper is None or self.scraper.output_format != output_format:
            self.scraper = JinaReaderScraper(
                api_key=self.jina_api_key,
                model=self.reader_model,
                output_format=output_format,
                # should read from config
                max_concurrent_requests=5,
                timeout=600
            )

    def forward(
        self,
        url: str,
        output_format: Optional[str] = "markdown"
    ) -> str:
        """
        Reads the content of a given URL and returns the processed text.

        Args:
            url (str): The URL to read content from.
            output_format (str, optional): The output format. Default is
                'markdown'.

        Returns:
            str: The processed content. If reading fails, return an error
                message string.
        """
        effective_output_format = (
            output_format if output_format is not None else "markdown"
        )
        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)

        log_func(f"[bold blue]Reading URL[/bold blue]: {url}")
        log_func(f"[dim]Parameters: output_format={effective_output_format}[/dim]")

        try:
            self._ensure_scraper(effective_output_format)
            # get the current or create a new event loop to run the async
            # scrape method
            # in FastAPI/Uvicorn environment, there should be a running loop
            # already
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # if there is no running loop (e.g. in a pure synchronous script),
                # create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # use the scraper's async context manager
            async def run_scrape():
                # ensure the scraper is properly handled in the async function
                if not self.scraper:
                    raise RuntimeError("Scraper not initialized")
                # assume the scraper implements __aenter__ and __aexit__
                async with self.scraper as scraper_instance:
                    return await scraper_instance.scrape(url)

            # run the async task
            result: ExtractionResult = loop.run_until_complete(run_scrape())

            if result.success:
                log_func(
                    f"[bold green]URL reading successful[/bold green]: {url} "
                    f"(content length: {len(result.content or '')})"
                )
                # return the scraped content, if empty return an empty string
                return result.content or ""
            else:
                log_func(
                    f"[bold red]URL reading failed[/bold red]: {url}, "
                    f"error: {result.error}"
                )
                return f"Error reading URL {url}: {result.error}"
        except Exception as e:
            log_func(
                f"[bold red]Unexpected error in ReadURLTool[/bold red]: {e}"
            )
            import traceback
            traceback.print_exc()
            return f"Unexpected error in ReadURLTool for {url}: {str(e)}"

    def setup(self):
        """Tool setup (if needed)."""
        # initialization can be done on demand in the first forward call
        pass
