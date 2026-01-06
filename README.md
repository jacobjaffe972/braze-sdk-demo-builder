# Code Generation Agent Repository

Multi-agent code generation system built with LangChain, LangGraph, and Gradio.

---

## Projects

### 1. Braze SDK Landing Page Generator
**Status**: In Development
**Location**: `/code/braze_code_gen/` (to be implemented)
**Purpose**: Generate fully functional, branded Braze SDK demo landing pages from natural language input.

**Features**:
- **Client Website Branding Extraction**: Analyze customer websites to extract color schemes and typography
- **6-Agent Workflow**: Lead agent → Research → Code Generation → Validation → Refinement → Finalization
- **Braze Docs MCP Integration**: Search 50+ cached Braze documentation pages for SDK guidance
- **Browser Testing**: Playwright integration for automated HTML/CSS/JS validation
- **HTML Export**: Download generated landing pages with metadata

**Documentation**: See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

### 2. Reference Agent Implementation
**Location**: [/code/reference_agents/](code/reference_agents/)
**Purpose**: Working examples of LangChain/LangGraph agent patterns. Reference code only - not used in production.

**Key Patterns**:
- ReAct Multi-Agent Delegation
- StateGraph Workflow Orchestration
- Factory Pattern with Type Safety
- Tool Integration (@tool decorators)
- Gradio UI with Metadata-Driven Configuration

**Pattern Documentation**: See [/docs/](docs/) directory

---

## MCP Server

### Braze Documentation MCP
**Location**: [/braze-docs-mcp/](braze-docs-mcp/)
**Purpose**: MCP server that scrapes and caches Braze documentation for agent access.

**Features**:
- Documentation search across 50+ pages
- Code example extraction
- Local caching (455KB cached data in `braze_docs_cache.json`)
- Resource access via `doc://{page_path}` URIs
- Search tool for finding relevant documentation

**Stack**: FastMCP, BeautifulSoup4, requests

---

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key
- (Optional) Tavily API key for web search

### Installation

1. **Clone Repository**
   ```bash
   cd /Users/Jacob.Jaffe/code-gen-agent
   ```

2. **Install Dependencies**
   ```bash
   cd code
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env  # If example exists

   # Or create .env with:
   OPENAI_API_KEY=your_openai_key_here
   TAVILY_API_KEY=your_tavily_key_here  # Optional
   BRAZE_API_KEY=your_braze_key_here
   BRAZE_BASE_URL=https://todd.braze.com
   ```

### Run Braze Code Generator

```bash
# Once implemented:
cd code
python run.py braze
```

### Run Reference Agents

```bash
cd code
python run.py react_multi_agent  # Deep research agent
python run.py rag_web_search     # Web search agent
python run.py llm_chaining       # Basic LLM chaining
```

---

## Documentation

### Implementation Plans
- [**IMPLEMENTATION_PLAN.md**](IMPLEMENTATION_PLAN.md) - Detailed Braze generator specification with 5-phase implementation

### Design Patterns
Comprehensive pattern documentation extracted from reference implementation:

- [**AGENT_PATTERNS.md**](docs/AGENT_PATTERNS.md) - ReAct delegation, StateGraph workflows, tool integration, Opik tracing
- [**FACTORY_PATTERN.md**](docs/FACTORY_PATTERN.md) - Factory pattern, AgentType enum, ChatInterface, agent registration
- [**TOOL_INTEGRATION.md**](docs/TOOL_INTEGRATION.md) - LangChain @tool decorators, MCP integration, safe evaluation, error handling
- [**UI_PATTERNS.md**](docs/UI_PATTERNS.md) - Gradio chat interfaces, metadata-driven config, state management
- [**WORKFLOW_ORCHESTRATION.md**](docs/WORKFLOW_ORCHESTRATION.md) - StateGraph, TypedDict state, conditional routing, testing

---

## Architecture

### Braze Code Generator Architecture

```
User Input (features + website URL)
    ↓
[1] Lead Agent
    ├─ Extract website URL
    ├─ Analyze website (colors, typography)
    ├─ Create feature plan with branding constraints
    └─ Store branding data in state
    ↓
[2] Research Agent
    ├─ Search Braze Docs MCP for SDK guidance
    ├─ Extract code examples
    └─ Collect implementation details
    ↓
[3] Code Generation Agent
    ├─ Generate HTML/CSS/JS with customer branding
    ├─ Apply color scheme to CSS variables
    ├─ Apply typography to font families
    └─ Create self-contained landing page
    ↓
[4] Validation Agent
    ├─ Test with Playwright (headless browser)
    ├─ Check Braze SDK initialization
    ├─ Verify form submissions
    └─ Report issues
    ↓
[5] Refinement Agent (if validation fails)
    ├─ Fix reported issues
    ├─ Re-test changes
    └─ Loop back to validation
    ↓
[6] Finalization Agent
    ├─ Polish code (comments, formatting)
    ├─ Export HTML file with metadata
    └─ Mark complete
    ↓
User downloads generated landing page
```

### Reference Agent Architecture

```
User selects agent mode
    ↓
Factory creates agent instance
    ↓
Main Orchestrator (ReActMultiAgent)
    ├─ Delegates to ToolUsingAgent
    ├─ Delegates to AgenticRAGAgent
    └─ Delegates to DeepResearchAgent
        ↓
DeepResearchAgent workflow (example):
    research_manager → specialized_research → evaluate
                            ↑                    ↓
                            └────────────────finalize
```

---

## Repository Structure

```
/Users/Jacob.Jaffe/code-gen-agent/
├── README.md                         # This file
├── IMPLEMENTATION_PLAN.md            # Braze generator specification
├── .env                              # API configuration (gitignored)
├── .gitignore                        # Ignore patterns
├── docs/                             # Design pattern documentation
│   ├── AGENT_PATTERNS.md
│   ├── FACTORY_PATTERN.md
│   ├── TOOL_INTEGRATION.md
│   ├── UI_PATTERNS.md
│   └── WORKFLOW_ORCHESTRATION.md
├── braze-docs-mcp/                   # MCP server (critical dependency)
│   ├── server.py                    # MCP implementation
│   ├── requirements.txt
│   ├── braze_docs_cache.json       # Cached docs (455KB)
│   └── README.md
└── code/
    ├── .gitignore
    ├── requirements.txt             # Python dependencies
    ├── run.py                       # Entry point
    ├── reference_agents/            # Reference implementation
    │   ├── README.md               # Reference code documentation
    │   ├── app.py                  # Gradio UI
    │   ├── core/                   # Factory and interfaces
    │   ├── agents/                 # ReAct multi-agent
    │   ├── tools/                  # Tool wrappers
    │   └── examples/               # Example outputs
    └── braze_code_gen/             # Production code (to be implemented)
        ├── agents/                 # 6 specialized agents
        ├── core/                   # State, models, workflow
        ├── tools/                  # Website analyzer, MCP tools, browser testing
        ├── prompts/                # Agent prompts
        ├── ui/                     # Gradio interface
        ├── utils/                  # Exporter, templates
        └── tests/                  # Unit and integration tests
```

---

## Development Workflow

### Current Phase: Repository Cleanup (Phase 0)
**Status**: ✅ Complete

- ✅ Created `/docs/` with 5 pattern documentation files
- ✅ Renamed `/code/deep_research/` to `/code/reference_agents/`
- ✅ Created `/code/reference_agents/README.md`
- ✅ Created root `/README.md`
- ⏳ Update `.gitignore` (next)
- ⏳ Git commit all changes (next)

### Next Phase: Foundation (Phase 1)
**Estimated Duration**: 3-4 days

1. Create `/code/braze_code_gen/` directory structure
2. Implement core state and models (`state.py`, `models.py`)
3. Implement website analyzer tool
4. Implement HTML exporter
5. Implement MCP integration tool
6. Implement browser testing tool
7. Create base HTML template
8. Update `requirements.txt`

### Subsequent Phases: Agents, Orchestration, UI, Testing
See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for complete 5-phase plan.

---

## Key Technologies

### Core Frameworks
- **LangChain** 0.3.x - LLM application framework
- **LangGraph** 0.2.x - Workflow orchestration with StateGraph
- **Gradio** 5.x - Web UI framework
- **Pydantic** 2.x - Data validation and structured outputs

### LLM & Tools
- **OpenAI** gpt-4o, gpt-4o-mini - Primary LLMs
- **Tavily** - Web search tool
- **MCP (Model Context Protocol)** - Documentation access

### Web & Testing
- **BeautifulSoup4** - HTML/CSS parsing
- **cssutils** - CSS parsing for branding extraction
- **Playwright** - Browser automation and testing
- **requests** - HTTP client

### Observability
- **Opik** - Tracing and monitoring for agent workflows

---

## Testing

### Unit Tests
```bash
cd code
pytest braze_code_gen/tests/test_agents.py -v
```

### Integration Tests
```bash
pytest braze_code_gen/tests/test_workflow.py -v
```

### Reference Implementation Tests
```bash
pytest reference_agents/test_agents.py -v
pytest reference_agents/test_gradio.py -v
```

---

## Contributing

This is a personal project repository. For questions or suggestions:
1. Review [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
2. Check pattern documentation in [/docs/](docs/)
3. Examine reference implementation in [/code/reference_agents/](code/reference_agents/)

---

## License

Private repository. Not licensed for distribution.

---

## Project Status

| Component | Status | Progress |
|-----------|--------|----------|
| Repository Cleanup | ✅ Complete | 100% |
| Pattern Documentation | ✅ Complete | 5/5 files |
| Braze Docs MCP | ✅ Working | 50+ pages cached |
| Reference Agents | ✅ Working | 9 agent modes |
| Braze Code Generator | 🚧 Not Started | 0% |

**Next Steps**: Begin Phase 1 (Foundation) - implement core state management and tools.

---

## References

- **LangChain**: https://python.langchain.com/
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Gradio**: https://www.gradio.app/
- **Opik**: https://www.comet.com/docs/opik/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Braze Docs**: https://www.braze.com/docs/
