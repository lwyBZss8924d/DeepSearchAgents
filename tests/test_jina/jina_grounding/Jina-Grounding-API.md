## Jina Grounding API

**Grounding API is a wrapper on top of `s.jina.ai` and `r.jina.ai`, adding CoT for planning and reasoning. **

### Core Functionality

The Jina Grounding API, accessible via `g.jina.ai`, is engineered to enhance the factual rigor of both AI-generated and human-authored content. It scrutinizes statements by cross-referencing them against current web data, assigning a factuality score and providing supporting or contradictory references. This process leverages Jina AI's suite of tools, including `s.jina.ai` for web searches and `r.jina.ai` for content extraction. Multi-hop reasoning, facilitated by Chain of Thought (CoT), ensures a comprehensive analysis.[^1]

### Architectural Overview

The API's architecture is a symphony of Large Language Models (LLMs) and specialized Jina AI services. LLMs generate search queries from input statements, which are then fed to `s.jina.ai` for web searches. The `r.jina.ai` API extracts content from the resulting web pages, and LLMs again sift through this data to extract relevant references and assess the statement's factuality.

### API Access and Configuration

The primary API endpoint is `https://g.jina.ai`, and it accepts the following parameters:

| Parameter | Description | Required |
| --- | --- | --- |
| statement | The statement to be fact-checked. | Yes |
| references | Allows manual specification of trusted websites. | No |

```
curl -X POST https://g.jina.ai \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $YOUR_JINA_TOKEN" \
     -d '{
           "statement":"Is the latest version of Jina AI's embeddings model `jina-embeddings-v3`?"
         }'
```

*YOUR_JINA_TOKEN is your Jina AI API key. You can get 1M free tokens from our homepage, which allows for about three or four free trials. With the current API pricing of 0.02USD per 1M tokens, each grounding request costs approximately $0.006.*

```json
{
  "code": 200,
  "status": 20000,
  "data": {
    "factuality": 0.95,
    "result": true,
    "reason": "The majority of the references explicitly support the statement that the last model released by Jina AI is jina-embeddings-v3. Multiple sources, such as the arXiv paper, Jina AI's news, and various model documentation pages, confirm this assertion. Although there are a few references to the jina-embeddings-v2 model, they do not provide evidence contradicting the release of a subsequent version (jina-embeddings-v3). Therefore, the statement that 'the last model released by Jina AI is jina-embeddings-v3' is well-supported by the provided documentation.",
    "references": [
      {
        "url": "https://arxiv.org/abs/2409.10173",
        "keyQuote": "arXiv September 18, 2024 jina-embeddings-v3: Multilingual Embeddings With Task LoRA",
        "isSupportive": true
      },
      {
        "url": "https://arxiv.org/abs/2409.10173",
        "keyQuote": "We introduce jina-embeddings-v3, a novel text embedding model with 570 million parameters, achieves state-of-the-art performance on multilingual data and long-context retrieval tasks, supporting context lengths of up to 8192 tokens.",
        "isSupportive": true
      },
      {
        "url": "https://azuremarketplace.microsoft.com/en-us/marketplace/apps/jinaai.jina-embeddings-v3?tab=Overview",
        "keyQuote": "jina-embeddings-v3 is a multilingual multi-task text embedding model designed for a variety of NLP applications.",
        "isSupportive": true
      },
      {
        "url": "https://docs.pinecone.io/models/jina-embeddings-v3",
        "keyQuote": "Jina Embeddings v3 is the latest iteration in the Jina AI’s text embedding model series, building upon Jina Embedding v2.",
        "isSupportive": true
      },
      {
        "url": "https://haystack.deepset.ai/integrations/jina",
        "keyQuote": "Recommended Model: jina-embeddings-v3 : We recommend jina-embeddings-v3 as the latest and most performant embedding model from Jina AI.",
        "isSupportive": true
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v2-base-en",
        "keyQuote": "The embedding model was trained using 512 sequence length, but extrapolates to 8k sequence length (or even longer) thanks to ALiBi.",
        "isSupportive": false
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v2-base-en",
        "keyQuote": "With a standard size of 137 million parameters, the model enables fast inference while delivering better performance than our small model.",
        "isSupportive": false
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v2-base-en",
        "keyQuote": "We offer an `encode` function to deal with this.",
        "isSupportive": false
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v3",
        "keyQuote": "jinaai/jina-embeddings-v3 Feature Extraction • Updated 3 days ago • 278k • 375",
        "isSupportive": true
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v3",
        "keyQuote": "the latest version (3.1.0) of [SentenceTransformers] also supports jina-embeddings-v3",
        "isSupportive": true
      },
      {
        "url": "https://huggingface.co/jinaai/jina-embeddings-v3",
        "keyQuote": "jina-embeddings-v3: Multilingual Embeddings With Task LoRA",
        "isSupportive": true
      },
      {
        "url": "https://jina.ai/embeddings/",
        "keyQuote": "v3: Frontier Multilingual Embeddings is a frontier multilingual text embedding model with 570M parameters and 8192 token-length, outperforming the latest proprietary embeddings from OpenAI and Cohere on MTEB.",
        "isSupportive": true
      },
      {
        "url": "https://jina.ai/news/jina-embeddings-v3-a-frontier-multilingual-embedding-model",
        "keyQuote": "Jina Embeddings v3: A Frontier Multilingual Embedding Model jina-embeddings-v3 is a frontier multilingual text embedding model with 570M parameters and 8192 token-length, outperforming the latest proprietary embeddings from OpenAI and Cohere on MTEB.",
        "isSupportive": true
      },
      {
        "url": "https://jina.ai/news/jina-embeddings-v3-a-frontier-multilingual-embedding-model/",
        "keyQuote": "As of its release on September 18, 2024, jina-embeddings-v3 is the best multilingual model ...",
        "isSupportive": true
      }
    ],
    "usage": {
      "tokens": 112073
    }
  }
}
```

The response of of grounding the statement, "The latest model released by Jina AI is jina-embeddings-v3," using `g.jina.ai` (as of Oct. 14, 2024).

[](https://jina.ai/news/fact-checking-with-new-grounding-api-in-jina-reader/#how-does-it-work "How Does It Work?")How Does It Work?
-----------------------------------------------------------------------------------------------------------------------------------

At its core, `g.jina.ai` wraps `s.jina.ai` and `r.jina.ai`, adding multi-hop reasoning through Chain of Thought (CoT). This approach ensures that each grounded statement is thoroughly analyzed with the help of online searches and document reading.

![Image 5: UI of Jina AI reader app, displaying three panels: User Input, Response, and User Render with interactive links and buttons a](https://jina-ai-gmbh.ghost.io/content/images/2024/10/User-Render.svg)

Grounding API is a wrapper on top of `s.jina.ai` and `r.jina.ai`, adding CoT for planning and reasoning.

### How Does It Work?

At its core, `g.jina.ai` wraps `s.jina.ai` and `r.jina.ai` , adding multi-hop reasoning through Chain of Thought (CoT). This approach ensures that each grounded statement is thoroughly analyzed with the help of online searches and document reading.

#### Step-by-Step Explanation

Let’s walk through the entire process to better understand how `g.jina.ai` handles grounding from input to final output:

1.   **Input Statement**:

The process begins when a user provides a statement they want to ground, such as _"The latest model released by Jina AI is jina-embeddings-v3."_ Note, there is no need to add any fact-checking instruction before the statement.
2.   **Generate Search Queries**:

An LLM is employed to generate a list of unique search queries that are relevant to the statement. These queries aim to target different factual elements, ensuring that the search covers all key aspects of the statement comprehensively.
3.   **Call `s.jina.ai` for Each Query**:

For each generated query, `g.jina.ai` performs a web search using `s.jina.ai`. The search results consist of a diverse set of websites or documents related to the queries. Behind the scene, `s.jina.ai` calls `r.jina.ai` to fetch the page content.
4.   **Extract References from Search Results**:

From each document retrieved during the search, an LLM extracts the key references. These references include:
    *   **`url`**: The web address of the source.
    *   **`keyQuote`**: A direct quote or excerpt from the document.
    *   **`isSupportive`**: A Boolean value indicating whether the reference supports or contradicts the original statement.

5.   **Aggregate and Trim References**:

All the references from the retrieved documents are combined into a single list. If the total number of references exceeds 30, the system selects 30 random references to maintain manageable output.
6.   **Evaluate the Statement**:

The evaluation process involves using an LLM to assess the statement based on the gathered references (up to 30). In addition to these external references, the model’s internal knowledge also plays a role in the evaluation. The final result includes:
    *   **`factuality`**: A score between 0 and 1 that estimates the factual accuracy of the statement.
    *   **`result`**: A Boolean value indicating whether the statement is true or false.
    *   **`reason`**: A detailed explanation of why the statement is judged as correct or incorrect, referencing the supporting or contradicting sources.

7.   **Output the Result**:

Once the statement has been fully evaluated, the output is generated. This includes the **factuality score**, the **assertion of the statement**, a **detailed reasoning**, and a list of **references** with citations and URLs. The references are limited to the citation, URL, and whether or not they support the statement, keeping the output clear and concise.

### Decoding the Response

The API dispenses a JSON payload with these key fields:

| Field | Description |
| --- | --- |
| code | HTTP status code. |
| status | Status code indicating success or failure. |
| data | factuality: A score between 0 and 1 indicating the factual accuracy.<br>          result: A boolean value indicating whether the statement is true or false.<br>          reason: A detailed explanation referencing supporting or contradicting sources.<br>          references: A list of references with URL, keyQuote, and isSupportive fields.<br>          usage: Token usage information.[^2] |


### Navigating Error States

The API signals errors through distinct error codes, covering scenarios such as invalid API keys, exceeded rate limits, or malformed statements. These messages are designed to provide actionable insights into the nature of the problem.

### Performance Metrics

Jina AI's internal evaluations tout an F1 score of 0.92 in fact-checking tasks, surpassing models like Gemini Pro and GPT-4. This benchmark was derived from testing the API against 100 statements with known truth values.[^3]

| Model | Precision | Recall | F1 Score |
| --- | --- | --- | --- |
| Jina AI Grounding API (g.jina.ai) | 0.96 | 0.88 | 0.92 |
| Gemini-flash-1.5-002 w/ grounding | 1.00 | 0.73 | 0.84 |
| Gemini-pro-1.5-002 w/ grounding | 0.98 | 0.71 | 0.82 |
| gpt-o1-mini | 0.87 | 0.66 | 0.75 |
| gpt-4o | 0.95 | 0.58 | 0.72 |
| Gemini-pro-1.5-001 w/ grounding | 0.97 | 0.52 | 0.67 |
| Gemini-pro-1.5-001 | 0.95 | 0.32 | 0.48 |


### Known Deficiencies

Despite its strengths, the API exhibits certain limitations:

*   **Latency**: Grounding requests can take up to 30 seconds, a potential bottleneck for real-time applications[^4].
*   **Token Consumption**: Each request can burn through as many as 300,000 tokens, impacting cost-effectiveness.
*   **Data Dependency**: The API's accuracy is inextricably linked to the quality of web sources, making it vulnerable to misinformation.
*   **Scope**: It's ill-suited for subjective opinions, speculative forecasts, or counterfactual scenarios.

### Ecosystem Integration

The Jina Grounding API plays well with other tools:

*   **Haystack**: The `JinaReaderConnector` component streamlines integration with Haystack, as illustrated below:

```python
from haystack_integrations.components.connectors.jina import JinaReaderConnector

reader = JinaReaderConnector(mode="ground")
query = "The latest model released by Jina AI is jina-embeddings-v3"
result = reader.run(query=query)
document = result["documents"][^0]
print(document.content)
```

*   **LobeChat**: Integration with LobeChat involves acquiring an API key from the Jina AI website and configuring it within LobeChat's settings.

### Use Cases

The API lends itself to several applications:

*   **Fact-Checking**: Validating claims in articles, blogs, and social media.
*   **Content Verification**: Ensuring the reliability of AI-generated content.
*   **Hallucination Mitigation**: Reducing inaccuracies in LLM outputs by grounding them in verifiable data.

### Authentication and Throttling

API keys, obtainable from the Jina AI website, are mandatory for authentication. Rate limits are enforced to maintain service quality and prevent abuse, with higher limits available on premium tiers. Jina AI offers 1M free API Tokens for initial use. To top up your key or use commercially, scroll on the API KEY & BILLING

### Cost Structure and Support

A free tier with restricted usage is available, while higher usage necessitates a premium API key. Pricing is determined by token consumption. Support is accessible through the Jina AI website and community forums.

### Future Trajectory

Jina AI's roadmap includes:

*   Enhancing accuracy and reliability.
*   Reducing latency and token usage.
*   Expanding data source compatibility.
*   Broadening integration with other platforms.

The Jina Grounding API presents a compelling solution for bolstering the credibility of AI and human-generated content. While it's not without its drawbacks, its potential impact on information integrity is undeniable. The question remains whether it can overcome its limitations to become a truly indispensable tool in the age of AI. The API key is required to access Jina AI's services and can be managed via the Jina AI website. For commercial use or to increase token limits, topping up the API key is necessary. To obtain and manage your API key, visit the Jina AI website and navigate to the API section.



[^1]: from haystack integrations components connectors jina import JinaReaderConnector [JinaReaderConnector - Haystack Documentation - Deepset](https://docs.haystack.deepset.ai/docs/jinareaderconnector)

[^2]: from haystack integrations components connectors jina import JinaReaderConnector [JinaReaderConnector - Haystack Documentation - Deepset](https://docs.haystack.deepset.ai/docs/jinareaderconnector)

[^3]: This document will guide you on how to use Jina AI in LobeChat Step 1 Obtain a Jina AI API Key Visit the Jina AI official website and click the API button Learn how to configure and use Jina AI models in LobeChat obtain an API key and start conversations LobeChat Jina AI API Key Web UI Jina AI provides each user with 1M free API Tokens and the API can be used without registration If you need to manage the API Key or recharge the API you Using Jina AI in LobeChat Step 1 Obtain a Jina AI API Key Step 2 Configure Jina AI in LobeChat Visit LobeChat s Application Settings interface Find the Step 1 Obtain a Jina AI API Key Find the API Key generated for you in the API Key menu below Copy and save the generated API Key Jina AI provides each user with 1M free API Tokens and the API can be used without registration If you need to manage the API Key or recharge the API you Step 2 Configure Jina AI in LobeChat Enable Jina AI and fill in the obtained API Key Select a Jina AI model for your assistant and start the conversation Jina AI is an open source neural search company founded in 2020 It focuses on using deep learning technology to process multimodal data [Using Jina AI API Key in LobeChat - LobeHub | Using Jina AI API Key in LobeChat ·  · LobeHub](https://lobehub.com/docs/usage/providers/jina)

[^4]: Jina AI API keys start with 10 million free tokens that you can use non commercially To top up your key or use commercially scroll on the API KEY BILLING Documentation for the Jina AI credentials Use these credentials to authenticate Jina AI in n8n a workflow automation platform Visit the Jina AI website Select API on the page Select API KEY BILLING in the API app widget API key A Jina AI API key You can get your free API key without creating an account by doing the following Visit the Jina AI website Select API on the page Tutorial Build an AI Refer to Jina AI s reader API documentation and Jina AI s search API documentation for more information about the service Visit the Jina AI website Select API on the page Select API KEY BILLING in the API app widget Copy the key labeled This is your unique key [Jina AI credentials - n8n Docs | Jina AI credentials | n8n Docs](https://docs.n8n.io/integrations/builtin/credentials/jinaai)
