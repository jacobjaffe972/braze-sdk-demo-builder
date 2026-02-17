# Braze SDK Demo Builder

**Multi-agent code generation system for creating branded Braze SDK demo landing pages**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-green.svg)](https://python.langchain.com/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()

---

## Overview

The Braze SDK Demo Builder is a **multi-agent system** that automatically creates fully functional, branded HTML landing pages featuring Braze SDK integrations. Built with LangGraph and supporting **multiple LLM providers** (OpenAI, Anthropic, Google), it streamlines the process of creating SDK demos for customers.

### Key Features

- **6-Agent Workflow**: Sequential pipeline with specialized agents for planning, research, generation, validation, refinement, and finalization
- **Automatic Branding**: Extracts colors and fonts from customer websites
- **Multi-Provider LLM Support**: Choose between OpenAI, Anthropic Claude, or Google Gemini
- **Browser Validation**: Playwright-based testing for code quality
- **Real-time Streaming**: Watch agents work with live progress updates
- **Single-File Output**: Self-contained HTML with inline CSS and JavaScript
- **Natural Language**: No coding required - describe what you want

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Architecture](#architecture)
- [Agent Details](#agent-details)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Further Reading](#further-reading)

---

## Prerequisites

### Required

- **Python 3.10+** - [Download here](https://www.python.org/downloads/)
- **LLM API key** (at least one):
  - OpenAI API key (default provider)
  - Anthropic API key
  - Google API key
- **Braze API credentials** - API key and SDK endpoint for the generated landing pages

### Optional

- **Playwright** - Enables automated browser validation of generated pages. The app works without it but skips the validation step.
- **Tavily API key** - For web search functionality
- **Opik API key** - For LLM observability/tracing

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jacobjaffe972/braze-sdk-demo-builder.git
   cd braze-sdk-demo-builder
   ```

2. **Install dependencies**:
   ```bash
   python3 -m pip install -r code/requirements.txt
   ```

   > **Multiple Python versions?** Make sure `pip` matches the `python3` you intend to use. If you have several versions installed, be explicit: `python3.13 -m pip install -r code/requirements.txt`.

3. **Install Playwright** (optional - for browser validation):
   ```bash
   playwright install chromium
   ```

   > If you encounter SSL certificate errors during Playwright tests, see [Troubleshooting](#playwright-ssl-certificate-errors) below.

4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Then edit `.env` with your credentials:
   ```bash
   # Choose your LLM provider: openai (default), anthropic, or google
   MODEL_PROVIDER=openai

   # Set the API key for your chosen provider
   OPENAI_API_KEY=sk-proj-...

   # Braze credentials (for the generated landing pages)
   BRAZE_API_KEY=your-braze-api-key
   BRAZE_SDK_ENDPOINT=your-sdk-endpoint.braze.com
   ```

---

## Quick Start

### Launch the Web UI

```bash
./launch.sh
```

Then open **http://localhost:7800** in your browser.

The launch script auto-detects which Python has the required packages. To override, set `PYTHON`:
```bash
PYTHON=python3.13 ./launch.sh
```

The Chainlit chat UI will prompt you for Braze API credentials (or auto-load them from `.env`), then you can describe the landing page you want in natural language.

To use a custom port:
```bash
./launch.sh 8080
```

### Programmatic Usage

```python
from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig

orchestrator = Orchestrator(
    braze_api_config=BrazeAPIConfig(
        api_key="your_api_key",
        rest_endpoint="https://rest.iad-01.braze.com",
        validated=True
    ),
    enable_browser_testing=True
)

result = orchestrator.generate(
    user_message="Create a landing page with push notifications for https://nike.com",
    website_url="https://nike.com"
)

print(f"Generated: {result['export_file_path']}")
```

---

## LLM Provider Configuration

The generator supports **three LLM providers** with simple environment-based switching:

### Quick Setup

```bash
# Option 1: OpenAI (default)
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...

# Option 2: Anthropic Claude
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option 3: Google Gemini
MODEL_PROVIDER=google
GOOGLE_API_KEY=...
```

### Model Tiers

The system uses a three-tier architecture for optimal cost/performance:

| Tier       | Purpose                   | OpenAI       | Anthropic         | Google              |
|------------|---------------------------|--------------|-------------------|---------------------|
| **Primary**    | Code generation, planning | gpt-4o       | claude-opus-4-5   | gemini-2.0-flash    |
| **Research**   | Documentation search      | gpt-4o-mini  | claude-sonnet-4-5 | gemini-2.0-flash    |
| **Validation** | Code validation           | gpt-4o-mini  | claude-sonnet-4-5 | gemini-2.0-flash    |

### Cost Comparison

| Provider   | Est. Cost per Run* | Best For                |
|------------|-------------------|-------------------------|
| OpenAI     | ~$0.10            | Balance of cost/quality |
| Anthropic  | ~$0.40            | Highest code quality    |
| Google     | ~$0.002           | Cost efficiency         |

*Approximate cost for typical landing page generation

### Advanced: Programmatic Model Override

```python
from braze_code_gen.core.models import LLMConfig, ModelProvider
from braze_code_gen.core.llm_factory import LLMFactory

config = LLMConfig(
    provider=ModelProvider.ANTHROPIC,
    anthropic_api_key="sk-ant-...",
    model_mappings={
        "anthropic": {
            "primary": "claude-opus-4-5-20251101",
            "research": "claude-haiku-3-5-20250312",
            "validation": "claude-sonnet-4-5-20250929"
        }
    }
)

factory = LLMFactory(config)
```

**For detailed configuration**, see [LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md).

---

## Architecture

### Multi-Agent Workflow

```
User Input (features + website URL)
    ↓
[1] Planning Agent
    ├─ Extract website URL from natural language
    ├─ Analyze website (colors, fonts, branding)
    ├─ Create structured feature plan
    └─ Map features to Braze SDK methods
    ↓
[2] Research Agent
    ├─ Search official Braze MCP server (comprehensive docs)
    ├─ Use semantic search for better relevance
    ├─ Extract code examples with context
    └─ Get setup checklists and best practices
    ↓
[3] Code Generation Agent
    ├─ Generate HTML/CSS/JS with customer branding
    ├─ Apply extracted color scheme
    ├─ Apply typography settings
    ├─ Integrate Braze SDK initialization
    └─ Create self-contained landing page
    ↓
[4] Validation Agent
    ├─ Test with Playwright (headless browser)
    ├─ Verify Braze SDK loading
    ├─ Check JavaScript console for errors
    ├─ Validate form submissions
    └─ Generate validation report
    ↓
[5] Refinement Agent (if validation fails, max 3 iterations)
    ├─ Analyze validation issues
    ├─ Apply targeted fixes
    ├─ Preserve branding and functionality
    └─ Loop back to validation
    ↓
[6] Finalization Agent
    ├─ Polish code (comments, formatting)
    ├─ Inject metadata
    ├─ Export HTML file with JSON sidecar
    └─ Mark workflow complete
    ↓
User downloads generated landing page
```

### Tech Stack

- **Orchestration**: LangGraph (StateGraph pattern)
- **LLMs**: Multi-provider (OpenAI, Anthropic, Google) via LangChain
- **UI**: Chainlit (chat-based interface with WebSocket streaming)
- **Validation**: Playwright (headless browser testing)
- **Documentation**: Official Braze MCP server (semantic search)
- **Observability**: Opik tracing
- **Web Scraping**: BeautifulSoup4, cssutils
- **Data Validation**: Pydantic 2.x

### Real-time Streaming

LangGraph's `graph.stream()` only yields chunks after each node finishes. To provide real-time token streaming, the UI:

1. Opens a Chainlit Step **proactively** before each node starts
2. Predicts the next node when the current one completes
3. Drains a thread-safe `Queue` of tokens into the active Step via `stream_token()`

This gives smooth, live output while preserving the collapsible per-agent Step structure.

### Repository Structure

```
braze-sdk-demo-builder/
├── .env.example              # Environment template
├── README.md                 # This file
├── launch.sh                 # Launch script (Chainlit UI)
│
├── code/                     # Main application
│   ├── .chainlit/            # Chainlit config (theme, settings)
│   ├── public/               # Static assets (logo, CSS)
│   ├── chainlit.md           # In-chat welcome content
│   ├── requirements.txt      # Python dependencies
│   └── braze_code_gen/       # Core package
│       ├── chainlit_app.py   # Chainlit entry point
│       ├── agents/           # 6 specialized agents + orchestrator
│       ├── core/             # Workflow, models, LLM factory
│       ├── docs/             # LLM configuration guide
│       ├── prompts/          # System prompts
│       ├── tests/            # Test suites
│       ├── tools/            # MCP, browser testing, website analyzer
│       ├── ui/               # Chainlit callbacks
│       └── utils/            # Exporter, debug, HTML helpers
│
└── docs/                     # Architecture & patterns
    ├── AGENT_PATTERNS.md
    ├── DEMO_WORKFLOW_DIAGRAM.md
    ├── FACTORY_PATTERN.md
    ├── IMPLEMENTATION_PLAN.md
    ├── MCP_INTEGRATION.md
    ├── TOOL_INTEGRATION.md
    ├── WORKFLOW_DIAGRAMS.md
    ├── WORKFLOW_EXPLAINED.md
    └── WORKFLOW_ORCHESTRATION.md
```

---

## Agent Details

| Agent | Purpose | Tier | Temp | Tools |
|-------|---------|------|------|-------|
| **Planning** | Analyze request, extract URL, scrape branding, create feature plan | Primary | 0.3 | Website analyzer |
| **Research** | Search Braze docs for SDK methods, code examples, best practices | Research | 0.3 | `search_braze_docs`, `get_braze_code_examples` |
| **Code Generation** | Generate self-contained HTML/CSS/JS with customer branding and SDK integration | Primary | 0.7 | -- |
| **Validation** | Run Playwright browser tests, verify SDK loading, check JS console | Validation | 0.3 | Browser tester |
| **Refinement** | Fix validation issues with minimal targeted changes (max 3 iterations) | Primary | 0.5 | -- |
| **Finalization** | Polish code, inject metadata, export HTML file with JSON sidecar | Primary | 0.3 | Exporter |

Tier assignments map to the provider-specific models in the [Model Tiers](#model-tiers) table above.

---

## API Reference

### `Orchestrator`

```python
class Orchestrator:
    def __init__(
        self,
        braze_api_config: Optional[BrazeAPIConfig] = None,
        enable_browser_testing: bool = True,
        export_dir: str = "/tmp/braze_exports",
        opik_project_name: str = "braze-code-generator"
    )

    def generate(
        self,
        user_message: str,
        website_url: Optional[str] = None,
        max_refinement_iterations: int = 3
    ) -> Dict[str, Any]

    def generate_streaming(
        self,
        user_message: str,
        website_url: Optional[str] = None,
        max_refinement_iterations: int = 3
    ) -> Generator[Dict[str, Any], None, None]
```

### `BrazeAPIConfig`

```python
class BrazeAPIConfig(BaseModel):
    api_key: str          # Min 32 characters
    rest_endpoint: str    # Must start with https://
    validated: bool = False
```

### `CodeGenerationState`

TypedDict defining the workflow state passed between agents:

```python
class CodeGenerationState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    user_request: str
    feature_plan: Optional[SDKFeaturePlan]
    research_results: Optional[ResearchResult]
    generated_code: Optional[GeneratedCode]
    validation_passed: bool
    validation_errors: List[str]
    refinement_iteration: int
    max_refinement_iterations: int
    customer_website_url: Optional[str]
    branding_data: Optional[BrandingData]
    braze_api_config: Optional[BrazeAPIConfig]
    export_file_path: Optional[str]
    error: Optional[str]
```

---

## Testing

### Run All Tests

```bash
cd code/braze_code_gen/tests
./run_tests.sh
```

### Run Specific Test Suites

```bash
# Unit tests
pytest tests/test_agents.py -v

# Workflow integration tests
pytest tests/test_workflow.py -v

# End-to-end tests
pytest tests/test_e2e.py -v
```

---

## Troubleshooting

### Playwright SSL Certificate Errors

If Playwright browser validation fails with SSL certificate errors, this is typically caused by corporate proxies or self-signed certificates on the machine. To fix:

1. **Set the environment variable** before running:
   ```bash
   export NODE_TLS_REJECT_UNAUTHORIZED=0
   ```

2. **Or install your system certificates** for Playwright's bundled Chromium:
   ```bash
   # macOS - export system certs and point Playwright to them
   security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/certs.pem
   security find-certificate -a -p /Library/Keychains/System.keychain >> /tmp/certs.pem
   export SSL_CERT_FILE=/tmp/certs.pem
   export REQUESTS_CA_BUNDLE=/tmp/certs.pem
   ```

> The website analyzer already handles SSL fallback automatically when scraping customer sites, but Playwright uses its own bundled browser which doesn't inherit system certificate settings by default.

### Common Issues

**"LLM API key not found"** - Set the key for your chosen provider in `.env`

**"Playwright not installed"** - Run `pip install playwright && playwright install chromium`

**"Port 7800 already in use"** - Use a custom port: `./launch.sh 8080`

**"Braze API configuration not set"** - Complete the API config step in the UI, or set credentials in `.env`

**Website branding extraction fails** - Some sites block scraping; the system falls back to Braze default branding. You can provide colors manually: "Use #000 as primary color"

### Debugging

```bash
# View detailed logs
tail -f /tmp/braze_exports/*.log
```

---

## Further Reading

- **[LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md)** - Provider setup, cost optimization, model mappings
- **[Workflow Diagrams](docs/WORKFLOW_DIAGRAMS.md)** - Visual Mermaid diagrams of system architecture
- **[Agent Patterns](docs/AGENT_PATTERNS.md)** - ReAct delegation, StateGraph workflows, tool integration
- **[Factory Pattern](docs/FACTORY_PATTERN.md)** - LLM factory, provider abstraction
- **[Tool Integration](docs/TOOL_INTEGRATION.md)** - MCP integration, browser testing, web scraping
- **[Workflow Orchestration](docs/WORKFLOW_ORCHESTRATION.md)** - LangGraph StateGraph, routing, error handling

---

## Built With

- [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) - Workflow orchestration
- [OpenAI](https://openai.com/) - GPT-4 models
- [Anthropic](https://www.anthropic.com/) - Claude models + Claude Code
- [Google](https://ai.google.dev/) - Gemini models
- [Chainlit](https://chainlit.io/) - Chat-based web interface
- [Playwright](https://playwright.dev/) - Browser automation
- [Braze](https://www.braze.com/) - SDK and documentation

---

## Security

- **API Keys**: Stored in Chainlit session memory only, not persisted to disk
- **Generated HTML**: Saved locally to the export directory, not uploaded anywhere
- **No External Services**: All processing is local (except LLM API calls and Braze MCP docs)

---

## License

Private repository. Not licensed for distribution.
