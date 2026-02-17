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

## Quick Links

- **[Detailed Documentation](code/braze_code_gen/README.md)** - Complete guide and API reference
- **[LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md)** - Multi-provider setup and cost optimization
- **[Workflow Diagrams](docs/WORKFLOW_DIAGRAMS.md)** - High level architecture and sequence diagrams
- **[Pattern Documentation](docs/)** - LangChain/LangGraph best practices

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Repository Structure](#repository-structure)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

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

# Initialize
orchestrator = Orchestrator(
    braze_api_config=BrazeAPIConfig(
        api_key="your_api_key",
        rest_endpoint="https://rest.iad-01.braze.com",
        validated=True
    ),
    enable_browser_testing=True
)

# Generate landing page
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

**For detailed configuration**, see [LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md).

---

## Repository Structure

```
braze-sdk-demo-builder/
├── .env.example              # Environment template
├── .gitignore                # Ignore patterns
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
│       ├── README.md         # Detailed documentation
│       ├── agents/           # 6 specialized agents
│       ├── core/             # Workflow, models, LLM factory
│       ├── docs/             # Product documentation
│       ├── prompts/          # System prompts
│       ├── tests/            # Test suites
│       ├── tools/            # MCP, browser testing, website analyzer
│       ├── ui/               # Callbacks and UI utilities
│       └── utils/            # Utilities and helpers
│
└── docs/                     # Architecture & patterns
    ├── AGENT_PATTERNS.md     # Agent design patterns
    ├── DEMO_WORKFLOW_DIAGRAM.md # Demo workflow overview
    ├── FACTORY_PATTERN.md    # Factory and interfaces
    ├── IMPLEMENTATION_PLAN.md # Architecture decisions
    ├── MCP_INTEGRATION.md    # MCP server integration
    ├── TOOL_INTEGRATION.md   # Tool usage patterns
    ├── WORKFLOW_DIAGRAMS.md  # Visual diagrams
    ├── WORKFLOW_EXPLAINED.md # Detailed workflow walkthrough
    └── WORKFLOW_ORCHESTRATION.md # StateGraph patterns
```

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

---

## Documentation

### Product Documentation
- **[Main Documentation](code/braze_code_gen/README.md)** - Complete user guide, API reference, troubleshooting
- **[LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md)** - Provider setup, cost optimization, model mappings
- **[UI Documentation](code/braze_code_gen/ui/README.md)** - Chainlit chat interface guide

### Architecture & Patterns
- **[Implementation Plan](docs/IMPLEMENTATION_PLAN.md)** - Architecture decisions, 5-phase development plan
- **[Agent Patterns](docs/AGENT_PATTERNS.md)** - ReAct delegation, StateGraph workflows, tool integration
- **[Factory Pattern](docs/FACTORY_PATTERN.md)** - LLM factory, provider abstraction
- **[Tool Integration](docs/TOOL_INTEGRATION.md)** - MCP integration, browser testing, web scraping
- **[Workflow Orchestration](docs/WORKFLOW_ORCHESTRATION.md)** - LangGraph StateGraph, routing, error handling
- **[Workflow Diagrams](docs/WORKFLOW_DIAGRAMS.md)** - Visual Mermaid diagrams of system architecture

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

### Debugging

```bash
# View detailed logs
tail -f /tmp/braze_exports/*.log
```

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

## License

Private repository. Not licensed for distribution.
