# Custom AI Provider

A generic OpenAI-compatible AI provider for Keep. Supports any API that follows the OpenAI API format, including:

- **GLM (智谱清言)**
- **MiniMax**
- **DeepSeek**
- **Qwen (通义千问)**
- **Kimi (月之暗面)**
- **Any OpenAI-compatible API**
- **Private deployment models**

## Features

- **Custom Base URL**: Connect to any OpenAI-compatible endpoint
- **Multiple Models**: Configure multiple models for automatic failover
- **Timeout Support**: Configurable request timeout
- **Structured Output**: Support for JSON structured output formats

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| API Key | Yes | Your API key/token |
| Base URL | Yes | The API endpoint (e.g., `https://api.deepseek.com/v1`) |
| Models | No | Comma-separated list of model IDs (first is default) |
| Timeout | No | Request timeout in seconds (default: 60) |

## Example Usage

```yaml
steps:
  - name: query-ai
    provider:
      config: "{{ providers.my_custom_ai }}"
      type: customai
    with:
      prompt: "Analyze this alert: {{ alert.name }}"
      model: "glm-4"  # Optional, uses first model if not specified
      system_prompt: "You are a helpful AI assistant."
```

## Failover

If multiple models are configured, the provider will automatically try the next model if one fails:

```yaml
# If glm-4 fails, it will automatically try glm-3, then qwen-2, etc.
models: "glm-4,glm-3,qwen-2"
```

## Supported Private Deployments

This provider can connect to private deployments like:

- Local LLM servers (Ollama, vLLM, etc.)
- Enterprise AI platforms
- Custom model endpoints
