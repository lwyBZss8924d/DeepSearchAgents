#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/wolfram.py
# code style: PEP 8

"""
Wolfram Alpha Agent Tool for DeepSearchAgents.
"""

import wolframalpha
from typing import Optional, Any
from smolagents import Tool


class WolframAlphaTool(Tool):
    name = "wolfram"
    description = """
    Performs computational, mathematical, and factual queries using
    Wolfram Alpha's computational knowledge engine.
    """
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to send to Wolfram Alpha",
        },
    }
    output_type = "string"

    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id
        if not self.app_id:
            print("Warning: WolframAlphaTool initialization missing app_id.")
            self.wolfram_client = None
        else:
            try:
                self.wolfram_client = wolframalpha.Client(self.app_id)
            except Exception as e:
                print(f"Error: Failed to initialize Wolfram Alpha client: {e}")
                self.wolfram_client = None

    # setup method is not strictly needed if client is initialized in __init__
    # def setup(self):
    #     pass

    def forward(self, query: str):
        # Check if client was initialized successfully
        if self.wolfram_client is None:
            return ("Error: Wolfram Alpha client not initialized "
                    "(missing APP ID or initialization failed).")

        try:
            # Send the query to Wolfram Alpha
            res = self.wolfram_client.query(query)

            # Process the results
            results = []
            # Use next(res.results).text for simple answers if available
            try:
                simple_answer = next(res.results).text
                if simple_answer:
                    print(f"WOLFRAM QUERY: {query}\n"
                          f"RESULT (simple): {simple_answer}")
                    return simple_answer
            except (StopIteration, AttributeError):
                # Fallback to processing pods if simple answer isn't available
                pass

            for pod in res.pods:
                if pod.title:
                    for subpod in pod.subpods:
                        if subpod.plaintext:
                            results.append({
                                'title': pod.title,
                                'result': subpod.plaintext
                            })

            # Initialize final_result with a default value
            final_result = "No results found."

            # Try to find a primary result pod
            primary_titles = [
                "Result", "Decimal approximation", "Value", "Exact result"
            ]
            for title in primary_titles:
                for r in results:
                    if r['title'] == title:
                        final_result = r['result']
                        break
                if final_result != "No results found.":
                    break

            # If no primary result, use the first available result
            if final_result == "No results found." and results:
                final_result = results[0]['result']

            print(f"WOLFRAM QUERY: {query}\nRESULT (pods): {final_result}")
            return final_result

        except Exception as e:
            error_message = f"Error querying Wolfram Alpha: {str(e)}"
            print(error_message)
            if hasattr(res, 'success') and res.success == 'false':
                return (f"Wolfram Alpha did not understand the query or "
                        f"found no results: {query}")
            elif hasattr(res, 'didyoumeans'):
                suggestions = ", ".join([d['val'] for d in res.didyoumeans])
                return ("Wolfram Alpha did not understand the query. "
                        f"Did you mean: {suggestions}?")
            return error_message


class EnhancedWolframAlphaTool(WolframAlphaTool):
    """Enhanced version of WolframAlphaTool with verbose logging."""
    def __init__(
        self,
        wolfram_app_id: Optional[str] = None,
        app_id: Optional[str] = None,
        cli_console: Optional[Any] = True,
        verbose: bool = False
    ):
        """Initialize.

        Args:
            wolfram_app_id: Optional Wolfram Alpha App ID
                (alias for app_id).
            app_id: Optional Wolfram Alpha App ID.
            cli_console: Optional console for detailed output.
            verbose: Whether to enable verbose logging.
        """
        # Use either wolfram_app_id or app_id,
        # with wolfram_app_id taking precedence
        effective_app_id = wolfram_app_id or app_id
        super().__init__(app_id=effective_app_id)
        self.cli_console = cli_console
        self.verbose = verbose

    def _log_verbose(self, message: str):
        """Record detailed logs if verbose mode is enabled
        and a console is provided."""
        if self.verbose:
            if self.cli_console:
                try:
                    from rich.console import Console
                    if isinstance(self.cli_console, Console):
                        self.cli_console.print(message)
                    else:
                        print(message)
                except ImportError:
                    print(message)
            else:
                print(message)

    def forward(self, query: str):
        """Execute query and record detailed logs."""
        self._log_verbose(
            f"[bold magenta]Executing "
            f"Wolfram Alpha calculation[/bold magenta]: {query}"
        )
        self._log_verbose("[cyan]Calculating...[/cyan]")

        result = super().forward(query)

        self._log_verbose("[bold green]Calculation completed[/bold green]")

        return result
