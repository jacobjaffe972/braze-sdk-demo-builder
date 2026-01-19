# Braze SDK Landing Page Generator

**Multi-agent code generation system for creating branded Braze SDK demo landing pages**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-green.svg)](https://python.langchain.com/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()

---

## Overview

The Braze SDK Landing Page Generator is a sophisticated **multi-agent system** that automatically creates fully functional, branded HTML landing pages featuring Braze SDK integrations. Built with LangGraph and supporting **multiple LLM providers** (OpenAI, Anthropic, Google), it streamlines the process of creating SDK demos for customers.

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

- [Installation](#installation)
- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Repository Structure](#repository-structure)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Development Status](#development-status)

---

## Installation

### Prerequisites

- Python 3.10+
- **LLM API key** (choose one):
  - OpenAI API key (default)
  - Anthropic API key
  - Google API key
- Braze API credentials
- (Optional) Playwright for browser testing

### Setup

1. **Clone and navigate**:
   ```bash
   git clone <repository-url>
   cd code-gen-agent
   ```

2. **Create virtual environment**:
   ```bash
   cd code
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright** (optional, for validation):
   ```bash
   playwright install chromium
   ```

5. **Configure environment**:
   ```bash
   # Copy template
   cp ../.env.example ../.env

   # Edit .env with your credentials
   # MODEL_PROVIDER=openai  # or anthropic, google
   # OPENAI_API_KEY=sk-...
   # BRAZE_API_KEY=edc26b45-1538-4a6c-bd3f-3b95ee52d784
   # BRAZE_SDK_ENDPOINT=sondheim.braze.com
   ```

---

## Quick Start

### Launch Web UI

```bash
# From repository root
cd code
python -m braze_code_gen

# Or directly with Streamlit
cd code
streamlit run braze_code_gen/ui/streamlit_app.py
```

Then open **http://localhost:7860** in your browser.

### Command Line Options

```bash
# Custom port
python -m braze_code_gen --port 8080

# Enable public sharing
python -m braze_code_gen --share

# Disable browser testing (faster)
python -m braze_code_gen --no-browser-testing

# Debug mode with detailed logs
python -m braze_code_gen --debug
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

## 📁 Repository Structure

```
code-gen-agent/
├── .env.example              # Environment template
├── .gitignore                # Ignore patterns
├── README.md                 # This file
│
├── braze-docs-mcp/           # MCP server for Braze documentation
│   ├── server.py             # MCP implementation
│   ├── requirements.txt      # MCP dependencies
│   └── braze_docs_cache.json # Cached docs (50+ pages)
│
├── code/                     # Main application
│   ├── requirements.txt      # Python dependencies
│   └── braze_code_gen/       # Braze Code Generator
│       ├── __main__.py       # Entry point
│       ├── README.md         # Detailed documentation
│       ├── agents/           # 6 specialized agents
│       ├── core/             # Workflow, models, LLM factory
│       ├── docs/             # Product documentation
│       ├── prompts/          # System prompts
│       ├── tests/            # Test suites
│       ├── tools/            # MCP, browser testing, website analyzer
│       ├── ui/               # Streamlit interface
│       └── utils/            # Utilities and helpers
│
└── docs/                     # Architecture & patterns
    ├── AGENT_PATTERNS.md     # Agent design patterns
    ├── FACTORY_PATTERN.md    # Factory and interfaces
    ├── IMPLEMENTATION_PLAN.md # Architecture decisions
    ├── TOOL_INTEGRATION.md   # Tool usage patterns
    ├── WORKFLOW_DIAGRAMS.md  # Visual diagrams
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
    ├─ Search Braze Docs MCP (50+ cached pages)
    ├─ Find SDK implementation guidance
    ├─ Extract code examples
    └─ Collect best practices
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
- **UI**: Streamlit with streaming support
- **Validation**: Playwright (headless browser testing)
- **Documentation**: Braze Docs MCP server (cached)
- **Observability**: Opik tracing
- **Web Scraping**: BeautifulSoup4, cssutils
- **Data Validation**: Pydantic 2.x

---

## Documentation

### Product Documentation
- **[Main Documentation](code/braze_code_gen/README.md)** - Complete user guide, API reference, troubleshooting
- **[LLM Configuration Guide](code/braze_code_gen/docs/LLM_CONFIGURATION.md)** - Provider setup, cost optimization, model mappings
- **[UI Documentation](code/braze_code_gen/ui/README.md)** - Streamlit interface guide

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

### Debugging

```bash
# Enable debug mode
python -m braze_code_gen --debug

# View detailed logs
tail -f /tmp/braze_exports/*.log
```

---

# Built with:

- [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) - Workflow orchestration
- [OpenAI](https://openai.com/) - GPT-4 models
- [Anthropic](https://www.anthropic.com/) - Claude models + Claude Code
- [Google](https://ai.google.dev/) - Gemini models
- [Streamlit](https://streamlit.io/) - Web interface
- [Playwright](https://playwright.dev/) - Browser automation
- [Braze](https://www.braze.com/) - SDK and documentation

---

## 📄 License

Private repository. Not licensed for distribution.

---
