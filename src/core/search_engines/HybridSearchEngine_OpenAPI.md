# 📋 HybridSearchEngine as OpenAPI API Style Analysis

This OpenAPI specification defines a Hybrid Search Engine API that aggregates search results from multiple providers such as Serper, XAI, Jina, and Exa. It allows users to perform unified searches across these providers with features like parallel execution, intelligent deduplication, and standardized result formatting.

## 🌐 Major Endpoints
- **GET /search** - Performs a search across multiple providers based on the provided query and parameters. Includes pagination support.

## 🤖 Schema Models
- **SearchResult** - Represents a single search result with fields like title, URL, content, and provider metadata.
- **SearchUsage** - Represents the token usage for the search operation, including total tokens, prompt tokens, and completion tokens.

## ✨ Special Features & Considerations
- **Provider Aggregation**: Supports merging results from multiple search providers using different aggregation strategies.
- **Deduplication**: Implements URL deduplication to ensure unique search results.
- **Parallel Execution**: Executes searches in parallel across providers to reduce latency. Now also supports asynchronous parallel execution.
- **Provider-Specific Parameters**: Allows passing provider-specific parameters to customize search behavior for each provider.
- **Pagination**: Implements pagination for the search results, with `page` and `per_page` parameters.
- **Asynchronous Support**: Added asynchronous search capabilities for improved performance.

```yaml
openapi: 3.1.0
info:
  title: Hybrid Search Engine API
  description: Aggregates search results from multiple providers.
  version: 1.0.0
servers:
  - url: /api/v1
    description: Main API server
paths:
  /search:
    get:
      summary: Perform a hybrid search across multiple providers
      description: Executes a search query across multiple search providers and aggregates the results.
      operationId: performHybridSearch
      parameters:
        - name: query
          in: query
          description: Search query string
          required: true
          schema:
            type: string
        - name: num
          in: query
          description: Number of results to return per provider
          schema:
            type: integer
            format: int32
            default: 10
        - name: providers
          in: query
          description: Comma-separated list of specific providers to use (serper, xai, jina, exa). Defaults to all available.
          schema:
            type: array
            items:
              type: string
        - name: aggregation_strategy
          in: query
          description: How to combine results (merge, round_robin, priority)
          schema:
            type: string
            enum:
              - merge
              - round_robin
              - priority
            default: merge
        - name: search_type
          in: query
          description: Type of search (auto, neural, keyword)
          schema:
            type: string
            enum:
              - auto
              - neural
              - keyword
            default: auto
        - name: include_domains
          in: query
          description: Comma-separated list of domains to include in the search
          schema:
            type: array
            items:
              type: string
        - name: exclude_domains
          in: query
          description: Comma-separated list of domains to exclude from the search
          schema:
            type: array
            items:
              type: string
        - name: start_date
          in: query
          description: Filter by start date (ISO format)
          schema:
            type: string
            format: date
        - name: end_date
          in: query
          description: Filter by end date (ISO format)
          schema:
            type: string
            format: date
        - name: page
          in: query
          description: Page number for pagination
          schema:
            type: integer
            format: int32
            minimum: 1
            default: 1
        - name: per_page
          in: query
          description: Number of results per page
          schema:
            type: integer
            format: int32
            minimum: 1
            maximum: 100
      responses:
        '200':
          description: Successful operation
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/SearchResult'
                  query:
                    type: string
                    description: The original search query
                  total_results:
                    type: integer
                    description: The total number of results found
                  page:
                    type: integer
                    description: The current page number
                  per_page:
                    type: integer
                    description: The number of results per page
                  total_pages:
                    type: integer
                    description: The total number of pages
                  results_by_provider:
                    type: object
                    description: Number of results from each provider
                    additionalProperties:
                      type: integer
                  usage:
                    $ref: '#/components/schemas/SearchUsage'
                  providers_used:
                    type: array
                    items:
                      type: string
                    description: List of providers used in the search
                  aggregation_strategy:
                    type: string
                    description: The aggregation strategy used
        '400':
          description: Invalid input
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Error message
components:
  schemas:
    SearchResult:
      type: object
      properties:
        title:
          type: string
          description: Title of the search result
        url:
          type: string
          description: URL of the search result
        content:
          type: string
          description: Content snippet of the search result
        snippet:
          type: string
          description: Snippet of the search result
        provider:
          type: string
          description: The provider that returned the result
        score:
          type: number
          format: float
          description: Relevance score of the result
        published_date:
          type: string
          format: date
          description: Publication date of the result
        author:
          type: string
          description: Author of the result
        provider_metadata:
          type: object
          description: Provider-specific metadata
          additionalProperties:
            type: string
      example:
        title: Example Search Result
        url: https://example.com/result
        content: This is an example search result.
        snippet: Example snippet.
        provider: serper
        score: 0.85
        published_date: 2024-01-01
        author: John Doe
        provider_metadata:
          page_map: {}
    SearchUsage:
      type: object
      properties:
        total_tokens:
          type: integer
          description: Total number of tokens used
        prompt_tokens:
          type: integer
          description: Number of tokens used in the prompt
        completion_tokens:
          type: integer
          description: Number of tokens used in the completion
        counting_method:
          type: string
          description: Method used for counting tokens
      example:
        total_tokens: 150
        prompt_tokens: 50
        completion_tokens: 100
        counting_method: aggregate
tags:
  - name: search
    description: Operations related to hybrid search
```
