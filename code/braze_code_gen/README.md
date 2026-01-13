

# Braze SDK Landing Page Generator

**Multi-agent code generation system for creating branded Braze SDK demo landing pages**

---

## Overview

The Braze SDK Landing Page Generator is a sophisticated multi-agent system that automatically creates fully functional, branded HTML landing pages featuring Braze SDK integrations. Built with LangGraph and powered by GPT-4, it streamlines the process of creating SDK demos for customers.

### Key Features

- **6-Agent Workflow**: Sequential pipeline with specialized agents for each task
- **Automatic Branding**: Extracts colors and fonts from customer websites
- **Browser Validation**: Optional Playwright-based testing for code quality
- **Real-time Streaming**: Watch agents work with live progress updates
- **Single-File Output**: Self-contained HTML with inline CSS and JavaScript
- **Easy Customization**: Natural language requests, no coding required

---

## Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Agent Details](#agent-details)
- [Configuration](#configuration)
- [Testing](#testing)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

---

## Architecture

### Multi-Agent Workflow

```
User Input
    ↓
Planning Agent (Feature planning + branding extraction)
    ↓
Research Agent (Braze documentation search)
    ↓
Code Generation Agent (HTML/CSS/JS creation)
    ↓
Validation Agent (Browser testing)
    ↓
Router (Tests passed?)
    ├─ Yes → Finalization Agent (Polish + export)
    └─ No  → Refinement Agent (Fix issues, max 3 iterations)
            ↓
            Back to Validation Agent
```

### Technology Stack

- **Orchestration**: LangGraph (StateGraph pattern)
- **LLMs**: Multi-provider support (OpenAI, Anthropic, Google)
  - Primary tier: GPT-4o / Claude Opus / Gemini 2.0 Flash
  - Research/Validation tier: GPT-4o-mini / Claude Sonnet / Gemini 2.0 Flash
- **UI**: Gradio (web interface with streaming)
- **Validation**: Playwright (headless browser testing)
- **Documentation**: Braze Docs MCP server (cached JSON)
- **Observability**: Opik tracing

### Directory Structure

```
braze_code_gen/
├── agents/          # 6 specialized agents
│   ├── planning_agent.py
│   ├── research_agent.py
│   ├── code_generation_agent.py
│   ├── validation_agent.py
│   ├── refinement_agent.py
│   └── finalization_agent.py
├── core/            # Core workflow logic
│   ├── state.py     # State management
│   ├── models.py    # Pydantic models
│   └── workflow.py  # LangGraph workflow
├── tools/           # Utilities
│   ├── mcp_integration.py    # Braze docs access
│   ├── website_analyzer.py   # Branding extraction
│   └── browser_testing.py    # Playwright tests
├── ui/              # Gradio interface
│   └── gradio_app.py
├── utils/           # Helper functions
│   ├── html_template.py
│   ├── exporter.py
│   ├── sdk_suggestions.py
│   └── debug.py
├── prompts/         # System prompts
│   └── BRAZE_PROMPTS.py
└── tests/           # Test suites
    ├── test_agents.py
    ├── test_workflow.py
    ├── test_ui.py
    └── test_e2e.py
```

---

## Installation

### Prerequisites

- Python 3.10+
- **LLM API key** (choose one):
  - OpenAI API key (default)
  - Anthropic API key
  - Google API key
- Braze API credentials (for SDK initialization)
- Playwright (optional, for browser testing)

### Setup

1. **Clone the repository**:
   ```bash
   cd /path/to/code-gen-agent
   ```

2. **Create virtual environment**:
   ```bash
   cd braze-docs-mcp
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   cd ../code
   pip install -r requirements.txt
   ```

4. **Install Playwright** (optional, for browser testing):
   ```bash
   playwright install chromium
   ```

5. **Configure environment** (`.env` file):
   ```bash
   # Choose your LLM provider
   MODEL_PROVIDER=openai  # Options: openai, anthropic, google

   # Add corresponding API key
   OPENAI_API_KEY=your_openai_key_here
   # ANTHROPIC_API_KEY=your_anthropic_key_here
   # GOOGLE_API_KEY=your_google_key_here

   # Braze credentials (optional defaults)
   BRAZE_API_KEY=edc26b45-1538-4a6c-bd3f-3b95ee52d784
   BRAZE_SDK_ENDPOINT=sondheim.braze.com
   ```

---

## Quick Start

### Launch the UI

```bash
# From repository root
./launch_ui.sh

# Or with Python
cd code
python -m braze_code_gen
```

Then open http://localhost:7860 in your browser.

### Command Line Options

```bash
# Custom port
python -m braze_code_gen --port 8080

# Enable public sharing
python -m braze_code_gen --share

# Disable browser testing (faster)
python -m braze_code_gen --no-browser-testing

# Debug mode
python -m braze_code_gen --debug

# Custom export directory
python -m braze_code_gen --export-dir /path/to/exports
```

---

## Usage

### Web UI Workflow

1. **Configure API** (Section 1):
   - Enter Braze API key
   - Enter REST endpoint
   - Click "Validate & Continue"

2. **Generate Page** (Section 2):
   - Describe features needed
   - Optionally include customer website URL for branding
   - Click "Generate" or use quick suggestions

3. **Preview & Export** (Section 3):
   - View live preview in iframe
   - Check extracted branding data
   - Download HTML file

### Programmatic Usage

```python
from braze_code_gen.agents.orchestrator import Orchestrator
from braze_code_gen.core.models import BrazeAPIConfig

# Initialize orchestrator
orchestrator = Orchestrator(
    braze_api_config=BrazeAPIConfig(
        api_key="your_api_key_here",
        rest_endpoint="https://rest.iad-01.braze.com",
        validated=True
    ),
    enable_browser_testing=True,
    export_dir="/tmp/braze_exports"
)

# Generate landing page
result = orchestrator.generate(
    user_message="Create a landing page with push notifications and user tracking for https://nike.com",
    website_url="https://nike.com",
    max_refinement_iterations=3
)

# Get export path
export_path = result["export_file_path"]
print(f"Generated: {export_path}")
```

### Streaming Usage

```python
# Stream real-time updates
for update in orchestrator.generate_streaming(
    user_message="Create push notification demo",
    website_url="https://nike.com"
):
    if update["type"] == "node_complete":
        print(update["status"])
    elif update["type"] == "error":
        print(f"Error: {update['message']}")
```

---

## Agent Details

### 1. Planning Agent

**Purpose**: Analyzes user requests and creates structured feature plan

**Capabilities**:
- URL extraction from natural language
- Website branding analysis (colors, fonts)
- Feature prioritization
- SDK method mapping

**Model**: GPT-4 (temperature: 0.3)

### 2. Research Agent

**Purpose**: Searches Braze documentation for implementation guidance

**Capabilities**:
- Documentation search via MCP server
- Code example extraction
- Best practices identification
- Method signature lookup

**Model**: GPT-4-mini (temperature: 0.3)
**Tools**: `search_braze_docs`, `get_braze_code_examples`, `list_braze_doc_pages`

### 3. Code Generation Agent

**Purpose**: Generates complete HTML landing page

**Capabilities**:
- Customer branding application
- Responsive design
- Braze SDK integration
- Error handling
- Accessibility features

**Model**: GPT-4 (temperature: 0.7)

### 4. Validation Agent

**Purpose**: Tests generated code in browser

**Capabilities**:
- Playwright browser automation
- SDK loading verification
- JavaScript error detection
- Console log analysis
- Screenshot capture

**Model**: GPT-4-mini (temperature: 0.3)

### 5. Refinement Agent

**Purpose**: Fixes validation issues

**Capabilities**:
- Targeted error fixes
- Minimal code changes
- Branding preservation
- Up to 3 refinement iterations

**Model**: GPT-4 (temperature: 0.5)

### 6. Finalization Agent

**Purpose**: Polishes code and prepares export

**Capabilities**:
- Code commenting
- Metadata injection
- Final formatting
- File export with JSON sidecar

**Model**: GPT-4 (temperature: 0.3)

---

## ⚙️ Configuration

### LLM Provider Configuration

The Braze Code Generator supports **multiple LLM providers**. Choose between OpenAI, Anthropic Claude, and Google Gemini based on your preferences and API availability.

**Quick Setup**:

```bash
# Option 1: Use OpenAI (default)
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...

# Option 2: Use Anthropic Claude
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option 3: Use Google Gemini
MODEL_PROVIDER=google
GOOGLE_API_KEY=...
```

**Model Tiers**:

| Tier       | Purpose                   | OpenAI       | Anthropic        | Google              |
|------------|---------------------------|--------------|------------------|---------------------|
| Primary    | Code generation           | gpt-4o       | claude-opus-4-5  | gemini-2.0-flash    |
| Research   | Documentation search      | gpt-4o-mini  | claude-sonnet-4-5| gemini-2.0-flash    |
| Validation | Code validation           | gpt-4o-mini  | claude-sonnet-4-5| gemini-2.0-flash    |

**Switching Providers**: Simply update `MODEL_PROVIDER` in your `.env` file and restart. No code changes needed!

For detailed configuration options, cost comparison, and troubleshooting, see [LLM Configuration Guide](docs/LLM_CONFIGURATION.md).

### Environment Variables

```bash
# LLM Provider (NEW)
MODEL_PROVIDER=openai  # Options: openai, anthropic, google

# LLM API Keys (provide based on MODEL_PROVIDER)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional defaults for UI
BRAZE_API_KEY=edc26b45-1538-4a6c-bd3f-3b95ee52d784
BRAZE_SDK_ENDPOINT=sondheim.braze.com

# Debug settings
DEBUG=false
LOG_LEVEL=INFO
```

### Orchestrator Configuration

```python
Orchestrator(
    braze_api_config=BrazeAPIConfig(...),  # API credentials
    enable_browser_testing=True,            # Playwright validation
    export_dir="/tmp/braze_exports",        # Output directory
    opik_project_name="braze-generator"    # Tracing project
)
```

### Model Selection

**Switching providers** is done via environment variables (see [LLM Provider Configuration](#llm-provider-configuration) above).

For advanced customization, you can programmatically override model mappings:

```python
from braze_code_gen.core.models import LLMConfig, ModelProvider
from braze_code_gen.core.llm_factory import LLMFactory

config = LLMConfig(
    provider=ModelProvider.ANTHROPIC,
    anthropic_api_key="sk-ant-...",
    model_mappings={
        "anthropic": {
            "primary": "claude-opus-4-5-20251101",
            "research": "claude-haiku-3-5-20250312",  # Use faster model
            "validation": "claude-sonnet-4-5-20250929"
        }
    }
)

factory = LLMFactory(config)
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
# UI tests
pytest tests/test_ui.py -v

# Workflow tests
pytest tests/test_workflow.py -v

# E2E tests
pytest tests/test_e2e.py -v

# Agent tests (some require agent method updates)
pytest tests/test_agents.py -v -k "initialization"
```

### Test Coverage

- **Unit Tests**: Individual agent functionality
- **Integration Tests**: Workflow orchestration and routing
- **E2E Tests**: Full pipeline with mocked LLMs
- **UI Tests**: Gradio interface and streaming

---

## Development

### Adding New Features

1. **New SDK Feature Suggestion**:
   Edit [utils/sdk_suggestions.py](utils/sdk_suggestions.py):
   ```python
   FEATURE_SUGGESTIONS.append({
       "id": "feature_id",
       "label": "Feature Name",
       "prompt": "Description for agent",
       "features": ["sdkMethod1()", "sdkMethod2()"],
       "icon": "🎯"
   })
   ```

2. **Modify Agent Behavior**:
   Edit agent prompts in [prompts/BRAZE_PROMPTS.py](prompts/BRAZE_PROMPTS.py)

3. **Change Workflow**:
   Edit [core/workflow.py](core/workflow.py) to modify routing or add nodes

### Debugging

```python
from braze_code_gen.utils.debug import (
    setup_logging,
    get_state_debugger,
    get_performance_tracker
)

# Enable detailed logging
setup_logging(level="DEBUG", detailed=True, log_file="app.log")

# Dump state at each node
debugger = get_state_debugger()
debugger.dump_state(state, node_name="planning", iteration=0)
debugger.print_state_summary(state)

# Track performance
tracker = get_performance_tracker()
tracker.start("code_generation")
# ... agent work ...
tracker.end("code_generation")
tracker.print_summary()
```

### Code Style

- **Formatting**: Follow PEP 8
- **Type Hints**: Use for all function signatures
- **Docstrings**: Google style for all public methods
- **Logging**: Use module-level loggers

---

## Troubleshooting

### Common Issues

**1. "OpenAI API key not found"**
```bash
export OPENAI_API_KEY=your_key_here
```

**2. "Playwright not installed"**
```bash
pip install playwright
playwright install chromium
```

**3. "Port 7860 already in use"**
```bash
python -m braze_code_gen --port 8080
```

**4. "Braze API configuration not set"**
- Complete Section 1 (API Configuration) in the UI before generating

**5. Slow generation times**
- Disable browser testing: `--no-browser-testing`
- Use faster models: Edit orchestrator to use `gpt-4o-mini`

**6. Website branding extraction fails**
- Some sites block scraping → Falls back to Braze default branding
- Provide colors manually in request: "Use #000 as primary color"

### Debug Mode

```bash
python -m braze_code_gen --debug
```

Creates detailed logs in `/tmp/braze_debug/` with:
- State dumps after each node
- Performance metrics
- Full LLM prompts and responses

### Get Help

- Check logs: `/tmp/braze_exports/*.log`
- Review state dumps: `/tmp/braze_debug/state_*.json`
- Open issue: [GitHub Issues](https://github.com/anthropics/claude-code/issues)

---

## API Reference

### Core Classes

#### `Orchestrator`

Main orchestrator for workflow execution.

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

#### `BrazeAPIConfig`

Braze API configuration model.

```python
class BrazeAPIConfig(BaseModel):
    api_key: str  # Min 32 characters
    rest_endpoint: str  # Must start with https://
    validated: bool = False
```

### State Management

#### `CodeGenerationState`

TypedDict defining workflow state.

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
