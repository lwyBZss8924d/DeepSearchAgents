import json
from typing import List, Optional
from smolagents import Tool
from ..core.chunk.segmenter import JinaAISegmenter


class ChunkTextTool(Tool):
    """
    Split long text into smaller chunks using Jina AI Segmenter API.
    """
    name = "chunk_text"
    description = (
        "Splits a given long text into smaller chunks using "
        "Jina AI Segmenter API."
    )
    inputs = {
        "text": {
            "type": "string",
            "description": "The long text to be chunked.",
        },
        "chunk_size": {
            "type": "integer",
            "description": "Target size for each chunk.",
            "default": 150,
            "nullable": True,
        },
        "chunk_overlap": {
            "type": "integer",
            "description": "Number of characters to overlap between chunks.",
            "default": 50,
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(
        self,
        default_chunk_size: int = 150,
        default_chunk_overlap: int = 50,
        cli_console=None,
        verbose: bool = False
    ):
        """
        Initialize ChunkTextTool.

        Args:
            default_chunk_size (int): Default chunk size.
            default_chunk_overlap (int): Default chunk overlap.
            cli_console: Optional rich.console.Console for verbose CLI output.
            verbose (bool): Whether to enable verbose logging.
        """
        super().__init__()
        # Segmenter instance can be created on demand
        self._segmenter_instance: Optional[JinaAISegmenter] = None
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.cli_console = cli_console
        self.verbose = verbose

    def _get_segmenter(self, chunk_size: int) -> JinaAISegmenter:
        """
        Get or create a JinaAISegmenter instance with specified parameters.

        Args:
            chunk_size (int): Target size for each chunk.

        Returns:
            JinaAISegmenter: A segmenter instance.
        """
        # Always create a new segmenter instance with the requested chunk size
        return JinaAISegmenter()

    def forward(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> str:
        """
        Execute text chunking and return a JSON string of the chunk list.

        Args:
            text (str): Text to be chunked.
            chunk_size (int, optional): Chunk size.
                                       Default is default_chunk_size.
            chunk_overlap (int, optional): Chunk overlap.
                                          Default is default_chunk_overlap.

        Returns:
            str: JSON string containing the list of text chunks.
        """
        effective_chunk_size = (
            chunk_size if chunk_size is not None
            else self.default_chunk_size
        )

        log_func = (
            self.cli_console.print
            if self.cli_console and self.verbose
            else lambda *args, **kwargs: None
        )

        log_func("[bold blue]Executing text chunking with Jina AI"
                 " Segmenter API[/bold blue]")
        log_func(f"[dim]Parameters: chunk_size={effective_chunk_size}[/dim]")

        if not text:
            log_func("[yellow]Input text is empty, returning empty list."
                     "[/yellow]")
            return "[]"

        try:
            segmenter = self._get_segmenter(effective_chunk_size)
            chunks: List[str] = segmenter.split_text(
                text=text,
                max_chunk_length=effective_chunk_size
            )

            log_func(
                f"[bold green]Text chunking completed, generated "
                f"{len(chunks)} chunks.[/bold green]"
            )

            # Convert chunk list to JSON string
            return json.dumps(chunks, ensure_ascii=False)

        except Exception as e:
            log_func(
                f"[bold red]Error during text chunking: {str(e)}[/bold red]"
            )
            return f"Error during text chunking: {str(e)}"

    def setup(self):
        """Tool setup (if needed)."""
        pass
