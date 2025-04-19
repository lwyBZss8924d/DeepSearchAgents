import os
import json
import asyncio
from typing import List, Optional, Dict
from smolagents import Tool
import torch
from ..core.ranking.jina_embedder import JinaAIEmbedder


class EmbedTextsTool(Tool):
    """
    Get embedding vectors for a list of texts.
    """
    name = "embed_texts"
    description = (
        "Generates embedding vectors for a list of texts using Jina AI."
    )
    inputs = {
        "texts": {
            "type": "string",
            "description": "A JSON string representing a list of texts to embed.",
        },
        "model": {
            "type": "string",
            "description": (
                "The embedding model to use "
                "(e.g., 'jina-embeddings-v3', 'jina-clip-v2')."
            ),
            "default": "jina-clip-v2",
            "nullable": True,
        },
        "task": {
            "type": "string",
            "description": (
                "Intended downstream task "
                "(e.g., 'retrieval.query', 'retrieval.passage')."
            ),
            "default": None,
            "nullable": True,
        },
        "normalized": {
            "type": "boolean",
            "description": "Whether to normalize the embeddings.",
            "default": False,
            "nullable": True,
        }
        # can add dimensions, truncate, etc. parameters as needed
    }
    # return a JSON string representing the list of embedding vectors
    output_type = "string"

    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        default_model: str = "jina-embeddings-v3",
        cli_console=None,
        verbose: bool = False
    ):
        """
        Initialize EmbedTextsTool.

        Args:
            jina_api_key (str, optional): Jina AI API key.
            default_model (str): The default embedding model to use.
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
        self.default_model = default_model
        # Embedder instance will be created when needed
        self._embedders: Dict[str, JinaAIEmbedder] = {}
        self.cli_console = cli_console
        self.verbose = verbose

    def _get_embedder(self, model_name: str) -> JinaAIEmbedder:
        """ Get or create Embedder instance based on model name. """
        if model_name not in self._embedders:
            self._embedders[model_name] = JinaAIEmbedder(
                api_key=self.jina_api_key,
                model=model_name
                # can add concurrency and timeout configuration
            )
        return self._embedders[model_name]

    def forward(
        self,
        texts: str,
        model: Optional[str] = None,
        task: Optional[str] = None,
        normalized: Optional[bool] = False
    ) -> str:
        """
        Execute text embedding and return a JSON string of the list of embedding vectors.

        Args:
            texts (str): A JSON string representing the list of texts.
            model (str, optional): The embedding model to use.
                Default: initial default_model.
            task (str, optional): Optional downstream task hint.
            normalized (bool, optional): Whether to normalize the embeddings.

        Returns:
            str: A JSON string representing the list of embedding vectors.
                If an error occurs, return an error message string.
        """
        effective_model = model if model is not None else self.default_model
        effective_normalized = normalized if normalized is not None else False

        log_func = (self.cli_console.print if self.cli_console and self.verbose
                    else lambda *args, **kwargs: None)
        log_func(f"[bold blue]Executing text embedding (model: {effective_model})[/bold blue]")

        try:
            # parse the input JSON string
            try:
                input_list: List[str] = json.loads(texts)
                if not isinstance(input_list, list):
                    raise ValueError(
                        "Input 'texts' must be a JSON string of a list."
                    )
                if not input_list:
                    log_func("[yellow]Input text list is empty, returning empty list.[/yellow]")
                    return "[]"
                log_func(f"[dim]Number of texts to embed: {len(input_list)}[/dim]")
            except json.JSONDecodeError:
                return "Error: Input 'texts' is not a valid JSON string."
            except ValueError as e:
                return f"Error: {e}"

            embedder = self._get_embedder(effective_model)

            # get the event loop and run the async embedding task
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def run_embed():
                async with embedder:
                    # Note: JinaEmbedder returns torch.Tensor
                    tensor_result: torch.Tensor = await embedder.get_embeddings_async(
                        input_list,
                        task=task,
                        normalized=effective_normalized
                    )
                    # convert Tensor to Python list
                    return tensor_result.tolist()

            embeddings_list: List[List[float]] = loop.run_until_complete(run_embed())

            log_func(f"[bold green]Text embedding completed, "
                    f"generated {len(embeddings_list)} vectors.[/bold green]")

            # convert the list of embedding vectors to a JSON string
            return json.dumps(embeddings_list)

        except Exception as e:
            log_func(f"[bold red]Error during text embedding: {str(e)}[/bold red]")
            return f"Error during text embedding: {str(e)}"

    def setup(self):
        """Tool setup (if needed)."""
        pass
