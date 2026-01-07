# Braze SDK Landing Page Code Generation Tool - Implementation Plan

## Executive Summary

Build a multi-agent code generation system that creates fully functional Braze SDK demo landing pages from natural language input. The system uses a sequential workflow with 6 specialized agents orchestrated through LangGraph's StateGraph pattern, integrating the Braze Docs MCP server for documentation access and Playwright for live browser validation.

## User Requirements Summary

- **Output Format**: Single self-contained HTML file with inline CSS/JS
- **Validation**: Live testing in headless browser (Playwright)
- **Agent Structure**: Sequential workflow (Lead → Research → CodeGen → Validation → Refinement → Finalization)
- **User Interface**: Hybrid chat + feature suggestions (Gradio)
- **Target Users**: Internal TAM team for creating SDK demos
- **Client Branding**: Landing pages must be branded for demo client (color scheme + typography)
- **Website Analysis**: User provides customer website URL → system extracts branding automatically
- **API Configuration**: User inputs Braze API key and REST endpoint via Gradio UI initialization form
- **Export Functionality**: User can download generated HTML file via download button in UI

## Architecture Overview

### Design Pattern
Following the proven delegation pattern from [react_multi_agent.py](code/deep_research/agents/react_multi_agent.py):
- Main `BrazeCodeGenerator` class delegates to specialized agents
- TypedDict state management with Pydantic models
- StateGraph workflow with conditional routing
- LangChain @tool wrappers for MCP integration
- Opik tracing for full observability

### Agent Workflow
```
User Opens Gradio UI
    ↓
API Configuration Form (validate API key + REST endpoint)
    ↓
User Input (Gradio chat: features + customer website URL)
    ↓
Lead Agent (extract URL → analyze website → create feature plan with branding)
    ↓
Research Agent (query Braze Docs MCP)
    ↓
Code Generation Agent (create HTML/CSS/JS with customer branding)
    ↓
Validation Agent (Playwright browser test)
    ↓
Router (tests passed?)
    ├─ Yes → Finalization Agent (export HTML file)
    └─ No → Refinement Agent (max 3 iterations)
        ↓
        Back to Validation Agent
    ↓
User Downloads HTML from UI
```

## Directory Structure

Create new module at `/Users/Jacob.Jaffe/code-gen-agent/code/braze_code_gen/`:

```
braze_code_gen/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── braze_code_generator.py      # Main orchestrator (ChatInterface implementation)
│   ├── lead_agent.py                # Feature planning from user input
│   ├── research_agent.py            # MCP documentation queries
│   ├── code_generation_agent.py     # HTML/CSS/JS generation
│   ├── validation_agent.py          # Playwright browser testing
│   ├── refinement_agent.py          # Error fixing
│   └── finalization_agent.py        # Polish and delivery
├── core/
│   ├── __init__.py
│   ├── state.py                     # CodeGenerationState TypedDict
│   ├── models.py                    # Pydantic models (SDKFeaturePlan, GeneratedCode, etc.)
│   └── workflow.py                  # StateGraph builder
├── tools/
│   ├── __init__.py
│   ├── mcp_integration.py           # LangChain @tool wrappers for MCP
│   ├── browser_testing.py           # Playwright test harness
│   ├── code_validation.py           # HTML/JS syntax validation
│   └── website_analyzer.py          # Website scraping for branding (color/typography extraction)
├── prompts/
│   ├── __init__.py
│   └── BRAZE_PROMPTS.py             # All system prompts
├── ui/
│   ├── __init__.py
│   ├── gradio_app.py                # Gradio interface
│   └── components.py                # UI components
├── utils/
│   ├── __init__.py
│   ├── html_template.py             # Base HTML template with Braze SDK
│   ├── sdk_suggestions.py           # Feature suggestion data
│   └── exporter.py                  # HTML export with metadata
└── tests/
    ├── __init__.py
    ├── test_agents.py               # Unit tests
    └── test_workflow.py             # Integration tests
```

## Critical Implementation Files

### 1. State Management
**File**: [braze_code_gen/core/state.py](code/braze_code_gen/core/state.py)

```python
class CodeGenerationState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    user_features: List[str]
    feature_plan: Optional[SDKFeaturePlan]
    documentation_snippets: List[str]
    code_examples: List[str]
    html_code: Optional[str]
    css_code: Optional[str]
    js_code: Optional[str]
    combined_html: Optional[str]
    test_results: Optional[BrowserTestResults]
    validation_errors: List[str]
    refinement_count: int
    next_step: str
    is_complete: bool

    # Branding & Configuration
    customer_website_url: Optional[str]
    branding_data: Optional[BrandingData]
    braze_api_config: Optional[BrazeAPIConfig]
    export_file_path: Optional[str]
```

**File**: [braze_code_gen/core/models.py](code/braze_code_gen/core/models.py)

Pydantic models:
- `SDKFeature` - Individual feature with name, description, priority
- `SDKFeaturePlan` - Complete plan from Lead Agent
- `GeneratedCode` - HTML/CSS/JS output
- `BrowserTestResults` - Playwright test results
- `RefinementSuggestion` - Error fixes
- `ColorScheme` - Extracted color palette (primary, secondary, accent, background, text)
- `TypographyData` - Font information (primary_font, heading_font, base_size, heading_scale)
- `BrandingData` - Complete branding info (website_url, colors, typography, extraction_success, fallback_used)
- `BrazeAPIConfig` - API credentials (api_key, rest_endpoint, validated)

### 2. Tool Integration Layer

**File**: [braze_code_gen/tools/mcp_integration.py](code/braze_code_gen/tools/mcp_integration.py)

Create LangChain @tool wrappers that call the Braze Docs MCP server:

```python
@tool("search_braze_docs")
def search_braze_docs(query: str) -> str:
    """Search Braze documentation for SDK guidance."""
    # Call MCP server's search_documentation tool

@tool("get_braze_code_examples")
def get_braze_code_examples(page_path: str) -> str:
    """Extract code examples from specific doc page."""
    # Call MCP server's extract_code_from_page tool

@tool("list_braze_docs")
def list_braze_docs() -> str:
    """List all available Braze docs."""
    # Call MCP server's list_documentation tool
```

**Key Challenge**: Bridge MCP server (stdio-based) to LangChain tools
- Use MCP SDK client to connect to server at runtime
- Handle async MCP calls in sync LangChain context
- Implement connection pooling/caching for performance

**File**: [braze_code_gen/tools/website_analyzer.py](code/braze_code_gen/tools/website_analyzer.py)

Create website analysis tool for branding extraction:

```python
class WebsiteAnalyzer:
    """Analyzes customer websites to extract branding information."""

    def analyze_website(self, url: str) -> BrandingData:
        """
        Extract branding from customer website.

        Returns:
            BrandingData with colors and typography, or default branding if extraction fails
        """
        # Fetch HTML with requests (10-second timeout)
        # Parse with BeautifulSoup4
        # Extract colors: inline styles, CSS variables, linked stylesheets
        # Extract typography: font-family, sizes, weights from CSS rules
        # Use frequency analysis to identify primary/secondary/accent colors
        # Fallback to default Braze branding if scraping blocked or fails
```

**Color Extraction Strategy**:
- Use `cssutils` library to parse CSS
- Extract from: inline styles, CSS variables, `<link>` stylesheets, computed styles
- Frequency analysis to determine color roles (primary/secondary/accent)
- Default branding: `primary="#3accdd"` (Braze teal), `accent="#f64060"` (Braze coral)

**Error Handling**:
- Connection timeout (10s) → retry once with 15s timeout
- 403/429 (blocked) → try different User-Agent, then fallback
- Invalid URL → return default branding with `fallback_used=True`
- No colors found → use Braze default palette

### 3. Workflow Builder
**File**: [braze_code_gen/core/workflow.py](code/braze_code_gen/core/workflow.py)

```python
def create_braze_workflow(...) -> CompiledGraph:
    workflow = StateGraph(CodeGenerationState)

    # Add nodes
    workflow.add_node("lead", lead_agent)
    workflow.add_node("research", research_agent)
    workflow.add_node("code_generation", code_gen_agent)
    workflow.add_node("validation", validation_agent)
    workflow.add_node("refinement", refinement_agent)
    workflow.add_node("finalization", finalization_agent)

    # Linear edges
    workflow.add_edge(START, "lead")
    workflow.add_edge("lead", "research")
    workflow.add_edge("research", "code_generation")
    workflow.add_edge("code_generation", "validation")

    # Conditional routing from validation
    workflow.add_conditional_edges(
        "validation",
        route_after_validation,  # Check test results + iteration count
        {"refine": "refinement", "finalize": "finalization"}
    )

    # Refinement loop
    workflow.add_edge("refinement", "validation")
    workflow.add_edge("finalization", END)

    return workflow.compile()
```

**Router Logic**:
```python
def route_after_validation(state: CodeGenerationState) -> str:
    if state["test_results"].passed:
        return "finalize"
    if state["refinement_count"] >= 3:
        return "finalize"  # Give up after 3 tries
    return "refine"
```

### 4. Browser Testing Integration
**File**: [braze_code_gen/tools/browser_testing.py](code/braze_code_gen/tools/browser_testing.py)

```python
class BrazeCodeTester:
    def __init__(self):
        self.browser = None
        self.playwright = None

    def start(self):
        """Start Playwright browser (headless)."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

    def test_html_code(self, html_code: str) -> Dict:
        """Test HTML in browser, return results."""
        # Create temp HTML file
        # Load in browser
        # Collect console errors, network errors
        # Take screenshot
        # Get performance metrics
        # Return BrowserTestResults dict
```

### 5. Main Orchestrator
**File**: [braze_code_gen/agents/braze_code_generator.py](code/braze_code_gen/agents/braze_code_generator.py)

```python
class BrazeCodeGenerator(ChatInterface):
    """Main orchestrator implementing ChatInterface."""

    def initialize(self) -> None:
        # Initialize LLM
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

        # Initialize MCP client
        initialize_mcp_client()

        # Initialize browser tester
        self.browser_tester = BrazeCodeTester()
        self.browser_tester.start()

        # Create agent instances
        self.lead_agent = LeadAgent(self.llm)
        self.research_agent = ResearchAgent(self.llm)
        # ... etc

        # Build workflow
        self.workflow = create_braze_workflow(...)

        # Initialize Opik tracer
        self.tracer = OpikTracer(
            graph=self.workflow.get_graph(xray=True),
            project_name="braze-code-generator"
        )

    def process_message(self, message: str, chat_history) -> str:
        """Process user request, return HTML file path."""
        # Create initial state
        # Invoke workflow with tracer
        # Save generated HTML to file
        # Return path
```

### 6. Individual Agents

**Lead Agent** [braze_code_gen/agents/lead_agent.py](code/braze_code_gen/agents/lead_agent.py):
- Parses user input (natural language)
- **NEW**: Extracts customer website URL from message (regex + LLM fallback)
- **NEW**: Calls `WebsiteAnalyzer.analyze_website()` to extract branding
- Creates structured `SDKFeaturePlan` with Pydantic (incorporating branding constraints)
- Prioritizes features
- Returns plan + branding data in state

**URL Extraction**:
- Regex pattern: `https?://[^\s]+` for explicit URLs
- LLM fallback for conversational input ("check out nike.com" → "https://www.nike.com")

**Branding Integration**:
- Include extracted colors/fonts in feature planning prompt
- Guide: "Use primary color for headers, accent color for CTAs"
- Pass branding context to downstream agents via state

**Research Agent** [braze_code_gen/agents/research_agent.py](code/braze_code_gen/agents/research_agent.py):
- Uses `create_react_agent` with MCP tools
- For each feature, calls `search_braze_docs()`
- Extracts code examples with `get_braze_code_examples()`
- Accumulates documentation snippets
- Returns snippets in state

**Code Generation Agent** [braze_code_gen/agents/code_generation_agent.py](code/braze_code_gen/agents/code_generation_agent.py):
- Takes feature plan + documentation + **branding data**
- Generates HTML structure
- **NEW**: Generates CSS with customer branding (CSS variables for colors/fonts)
- **NEW**: Generates Google Fonts imports for custom typography
- Generates JavaScript (Braze SDK init with API config + feature calls)
- Combines into single HTML file
- Returns `GeneratedCode` in state

**Branding Application**:
```css
:root {
    --primary-color: #3accdd;      /* From customer website */
    --accent-color: #f64060;       /* From customer website */
    --font-primary: 'Inter', sans-serif;  /* From customer website */
}
body { font-family: var(--font-primary); }
.btn-primary { background-color: var(--accent-color); }
```

**Font Imports**:
- Extract font names from `typography.primary_font` and `typography.heading_font`
- Generate: `@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');`
- Skip system fonts (Arial, Helvetica, serif, sans-serif)

**Validation Agent** [braze_code_gen/agents/validation_agent.py](code/braze_code_gen/agents/validation_agent.py):
- Calls `BrazeCodeTester.test_html_code()`
- Collects console errors, network errors
- Takes screenshot for debugging
- Returns `BrowserTestResults` in state

**Refinement Agent** [braze_code_gen/agents/refinement_agent.py](code/braze_code_gen/agents/refinement_agent.py):
- Analyzes validation errors
- Uses LLM to fix issues
- Regenerates corrected HTML
- Increments `refinement_count`
- Returns updated HTML in state

**Finalization Agent** [braze_code_gen/agents/finalization_agent.py](code/braze_code_gen/agents/finalization_agent.py):
- Adds code comments
- Adds usage instructions
- Final formatting polish
- **NEW**: Calls `HTMLExporter.export_landing_page()` to save file
- **NEW**: Generates filename: `braze_landing_{domain}_{timestamp}.html`
- **NEW**: Adds metadata comment to HTML with generation details
- **NEW**: Saves JSON sidecar with full metadata
- Sets `is_complete = True` and `export_file_path`
- Returns final HTML + file path

**Metadata Comment** (added to HTML):
```html
<!--
Braze SDK Landing Page
Generated: 2026-01-06T14:30:22
Customer Website: https://nike.com
Features: Push Notifications, User Tracking
Colors: Primary=#111, Accent=#ff6b35
Fonts: 'Helvetica Neue', sans-serif
-->
```

### 7. Streaming Support (NEW REQUIREMENT)

**Difficulty**: EASY to MODERATE
**Impact**: HIGH - Significantly improves UX by showing real-time progress
**Implementation Phase**: Phase 3 (Orchestration) + Phase 4 (UI)

#### Overview

Add real-time streaming of agent thoughts, intermediate steps, and responses to the Gradio UI. This provides transparency into the multi-agent workflow and keeps users informed during long-running operations (website scraping, code generation, browser validation).

#### What Users Will See

```
✓ Feature plan created with customer branding
✓ Braze documentation research complete
✓ Landing page code generated
⚠ Validation issues detected, starting refinement
✓ Code refined (iteration 1)
✓ Browser validation complete
✓ Landing page finalized and exported
```

#### Implementation Strategy

**File**: [braze_code_gen/core/workflow.py](code/braze_code_gen/core/workflow.py)

Add streaming method that wraps LangGraph's built-in `.stream()`:

```python
class BrazeCodeGeneratorWorkflow:
    def stream_workflow(self, state: CodeGenerationState):
        """Stream workflow execution with intermediate updates."""
        for chunk in self.graph.stream(state):
            # chunk is dict with node name as key
            node_name = list(chunk.keys())[0]
            node_output = chunk[node_name]

            # Yield status update
            yield {
                "type": "node_complete",
                "node": node_name,
                "status": self._format_node_status(node_name, node_output)
            }

            # If there's a message, yield it
            if "messages" in node_output and node_output["messages"]:
                last_message = node_output["messages"][-1]
                if hasattr(last_message, 'content'):
                    yield {
                        "type": "message",
                        "content": last_message.content
                    }

    def _format_node_status(self, node_name: str, output: dict) -> str:
        """Format node completion status for UI."""
        status_messages = {
            "lead": "✓ Feature plan created with customer branding",
            "research": "✓ Braze documentation research complete",
            "code_generation": "✓ Landing page code generated",
            "validation": "✓ Browser validation complete" if output.get("validation_passed") else "⚠ Validation issues detected, starting refinement",
            "refinement": f"✓ Code refined (iteration {output.get('refinement_iteration', 0)})",
            "finalization": "✓ Landing page finalized and exported"
        }
        return status_messages.get(node_name, f"✓ {node_name} complete")
```

**File**: [braze_code_gen/agents/braze_code_generator.py](code/braze_code_gen/agents/braze_code_generator.py)

Add streaming method to main orchestrator:

```python
class BrazeCodeGenerator:
    def generate_streaming(self, user_message: str, braze_config: BrazeAPIConfig, website_url: Optional[str] = None):
        """Generate landing page with streaming updates."""
        # Create initial state
        state = create_initial_state(user_message, braze_config, website_url)

        # Stream workflow
        for update in self.workflow.stream_workflow(state):
            yield update
```

**File**: [braze_code_gen/ui/gradio_app.py](code/braze_code_gen/ui/gradio_app.py)

Modify Gradio to support generator functions:

```python
def respond_streaming(message: str, history: List[Tuple[str, str]]):
    """Process message with streaming updates."""
    # Validate API config
    if not api_config:
        yield "⚠️ Please configure Braze API first"
        return

    # Extract website URL from message
    url_match = re.search(r'https?://[^\s]+', message)
    website_url = url_match.group(0) if url_match else None

    # Initialize generator
    generator = braze_generator.generate_streaming(message, api_config, website_url)

    # Stream updates
    status_text = ""
    for update in generator:
        if update["type"] == "node_complete":
            # Show progress status
            status_text += f"\n{update['status']}"
            yield status_text

        elif update["type"] == "message":
            # Show agent response
            yield status_text + f"\n\n{update['content']}"

# Create chat interface with streaming
demo = gr.ChatInterface(
    fn=respond_streaming,
    title="Braze SDK Landing Page Generator",
    type="messages"  # Important for streaming support
)
```

#### Token-Level Streaming (Optional Enhancement)

For even smoother UX, stream individual LLM tokens as they're generated using LangGraph's `.astream_events()`:

```python
async def astream_with_tokens(self, state: CodeGenerationState):
    """Stream workflow with token-level granularity."""
    async for event in self.graph.astream_events(state, version="v2"):
        # Stream LLM tokens
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, 'content') and chunk.content:
                yield {
                    "type": "token",
                    "content": chunk.content
                }

        # Stream node completions
        elif event["event"] == "on_chain_end":
            node_name = event.get("name", "")
            if node_name in ["lead", "research", "code_generation", ...]:
                yield {
                    "type": "node_complete",
                    "node": node_name
                }
```

**Requirements for Token Streaming**:
1. Make Gradio `respond` function `async`
2. Use `async for` to iterate over tokens
3. Update UI to handle async generators

#### Benefits

1. **User Experience**:
   - No more "black box" waiting
   - Clear progress indication during 30-60 second workflows
   - Confidence that system is working (especially during slow operations like website scraping)

2. **Debugging**:
   - See exactly where workflow fails
   - Identify slow agents (code generation can take 10-15 seconds)
   - Monitor validation loop iterations

3. **Transparency**:
   - Users see which agent is active
   - Understand decision points (validation pass/fail)
   - Watch code refinement iterations (up to 3)

#### Implementation Complexity

- **Basic Streaming** (node-level): **EASY** - 50-100 lines of code
  - Uses LangGraph's built-in `.stream()` method
  - Simple generator function pattern
  - No async complexity

- **Token Streaming**: **MODERATE** - Additional 150 lines
  - Requires async/await support
  - More complex event filtering
  - Gradio async handler setup

#### Recommendation

**Start with basic node-level streaming in Phase 3 & 4**. This provides 80% of the UX benefit with minimal complexity. Token-level streaming can be added later if users want even smoother text generation.

#### Code Changes Required

**No changes to Phase 1 & 2 agent code** - Streaming is purely an orchestration-layer concern. All 6 agents built in Phase 2 remain unchanged.

**New code in Phase 3 & 4**:
1. Add `stream_workflow()` method to [core/workflow.py](code/braze_code_gen/core/workflow.py)
2. Add `generate_streaming()` method to [agents/braze_code_generator.py](code/braze_code_gen/agents/braze_code_generator.py)
3. Modify `respond()` to generator function in [ui/gradio_app.py](code/braze_code_gen/ui/gradio_app.py)

**Total additional code**: ~100 lines

### 8. Gradio UI
**File**: [braze_code_gen/ui/gradio_app.py](code/braze_code_gen/ui/gradio_app.py)

**NEW: Three-Section Accordion Layout with Streaming Support**

```python
def create_braze_ui():
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        # State management
        api_config_state = gr.State(None)
        generated_html_state = gr.State(None)

        gr.Markdown("# Braze SDK Landing Page Generator")
        gr.Markdown("Create branded demo landing pages for Braze SDK integration")

        # SECTION 1: API Configuration (initially open, required first)
        with gr.Accordion("1. Configure Braze API", open=True) as api_section:
            api_key_input = gr.Textbox(
                label="Braze API Key",
                placeholder="Enter your Braze API key",
                type="password"
            )
            rest_endpoint_input = gr.Textbox(
                label="REST Endpoint",
                placeholder="https://rest.iad-01.braze.com",
                value="https://todd.braze.com"  # Default from .env
            )
            validate_btn = gr.Button("Validate & Continue", variant="primary")
            validation_status = gr.Markdown("")

        # SECTION 2: Chat Interface (enabled after API validation)
        with gr.Accordion("2. Generate Landing Page", open=False) as chat_section:
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(height=400)
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Describe your landing page",
                            placeholder="Include customer website URL and features needed",
                            lines=2
                        )
                        submit = gr.Button("Generate", variant="primary")

                with gr.Column(scale=1):
                    gr.Markdown("### Quick Suggestions")
                    push_btn = gr.Button("Push Notifications", size="sm")
                    tracking_btn = gr.Button("User Tracking", size="sm")
                    iam_btn = gr.Button("In-App Messages", size="sm")
                    cards_btn = gr.Button("Content Cards", size="sm")

        # SECTION 3: Preview & Export (shown after generation)
        with gr.Accordion("3. Preview & Export", open=False) as export_section:
            with gr.Row():
                preview_iframe = gr.HTML(label="Preview")
            with gr.Row():
                branding_preview = gr.JSON(label="Extracted Branding")
            with gr.Row():
                download_btn = gr.File(label="Download HTML", interactive=False)
                download_button = gr.Button("Export Landing Page", variant="primary")

        # Event Handlers
        validate_btn.click(
            fn=validate_api_config,
            inputs=[api_key_input, rest_endpoint_input],
            outputs=[validation_status, api_config_state, api_section, chat_section]
        )

        submit.click(
            fn=respond,
            inputs=[msg, chatbot, api_config_state],
            outputs=[chatbot]
        ).then(
            fn=lambda: gr.Accordion(open=True),
            outputs=[export_section]
        )

        download_button.click(
            fn=export_html,
            inputs=[generated_html_state],
            outputs=[download_btn]
        )
```

**API Validation Logic**:
```python
def validate_api_config(api_key, rest_endpoint):
    """Validate Braze API credentials."""
    if not api_key or len(api_key) < 20:
        return "❌ Invalid API key format", None, gr.Accordion(open=True), gr.Accordion(open=False)

    if not rest_endpoint.startswith("https://"):
        return "❌ REST endpoint must be HTTPS URL", None, gr.Accordion(open=True), gr.Accordion(open=False)

    config = BrazeAPIConfig(api_key=api_key, rest_endpoint=rest_endpoint, validated=True)

    return (
        "✅ API configuration validated! You can now generate landing pages.",
        config,
        gr.Accordion(open=False),  # Close API section
        gr.Accordion(open=True)    # Open chat section
    )
```

**UI Flow**:
1. User opens UI → API Configuration form shown
2. User enters API key + REST endpoint → Click "Validate & Continue"
3. Validation success → API section collapses, Chat section opens
4. User enters message with website URL → Click "Generate"
5. System shows progress → Agent workflow executes
6. Preview section opens → Shows iframe preview + branding data
7. User clicks "Export Landing Page" → Downloads HTML file

### 8. Prompts
**File**: [braze_code_gen/prompts/BRAZE_PROMPTS.py](code/braze_code_gen/prompts/BRAZE_PROMPTS.py)

Define all system prompts:
- `LEAD_AGENT_PROMPT` - Feature planning instructions **+ branding context**
- `RESEARCH_AGENT_PROMPT` - Documentation search instructions
- `CODE_GEN_PROMPT` - Code generation template **+ branding application guidance**
- `REFINEMENT_PROMPT` - Error fixing template
- `FINALIZATION_PROMPT` - Polishing template

**Example Enhanced Prompts**:

```python
LEAD_AGENT_ENHANCED_PROMPT = """
Create a feature plan for a Braze SDK landing page.

CUSTOMER BRANDING:
- Primary Color: {primary_color}
- Accent Color: {accent_color}
- Primary Font: {primary_font}
- Heading Font: {heading_font}

USER REQUEST: {user_request}

Design guidance: Use primary color for headers, accent color for CTAs.
"""

CODE_GEN_ENHANCED_PROMPT = """
Generate HTML/CSS/JS for Braze SDK demo landing page.

BRANDING: Primary={primary_color}, Accent={accent_color}
FONTS: Primary={primary_font}, Heading={heading_font}
FEATURES: {feature_list}
BRAZE API CONFIG: {api_key}, {rest_endpoint}

Use provided colors for headers, CTAs, and primary UI elements.
Apply custom typography throughout.
Initialize Braze SDK with provided API credentials.
Generate single self-contained HTML file.
"""
```

## Key Integration Points

### 1. MCP Server Connection
The Braze Docs MCP server ([braze-docs-mcp/server.py](braze-docs-mcp/server.py)) is configured in [.claude/.mcp.json](.claude/.mcp.json) but not yet connected to agents.

**Solution**: Create `BrazeDocsMCPClient` class that:
- Connects to stdio-based MCP server
- Exposes async methods for each MCP tool
- Wraps in LangChain @tool decorators
- Handles connection lifecycle

### 2. Playwright Setup
**New Dependency**: Add to [code/requirements.txt](code/requirements.txt):
```
playwright>=1.40.0
```

**Installation**: Run `playwright install chromium` after pip install

### 3. Gradio Integration
Use existing Gradio pattern from [code/deep_research/app.py](code/deep_research/app.py):
- Similar chat interface
- Add feature suggestion buttons
- Add iframe preview for generated HTML

## Error Handling & Iteration Limits

1. **Refinement Iterations**: Maximum 3 (hardcoded in router)
2. **Browser Test Timeout**: 10 seconds per page load
3. **MCP Call Timeout**: 5 seconds per documentation query
4. **Recursion Limit**: 50 for workflow invocation
5. **Graceful Degradation**: If validation fails after 3 tries, still deliver code with warnings

## Testing Strategy

### Unit Tests
- Test each agent creates valid state updates
- Test MCP tools return proper formats
- Test browser tester catches errors
- Test router logic with different states

### Integration Tests
- Test full workflow end-to-end
- Test refinement loop iterations
- Test error recovery

### Manual Testing
- Generate pages with various feature combinations
- Verify Braze SDK actually works
- Test in different browsers

## Dependencies to Add

Update [code/requirements.txt](code/requirements.txt):
```
# Existing dependencies...

# Browser testing
playwright>=1.40.0

# MCP SDK (if not already present)
mcp>=1.0.0

# Website Analysis (NEW)
cssutils>=2.9.0        # CSS parsing and manipulation
webcolors>=1.13        # Color name to hex conversion

# Already available from braze-docs-mcp:
# beautifulsoup4>=4.12.0
# requests>=2.31.0
# lxml>=4.9.0
```

## Implementation Sequence

### Phase 1: Foundation (Start Here)
1. Create directory structure
2. Implement `core/state.py` and `core/models.py`
3. Implement `tools/mcp_integration.py` (critical path)
4. Implement `tools/browser_testing.py`
5. Create base HTML template in `utils/html_template.py`

### Phase 2: Agents
6. Implement Lead Agent (simplest)
7. Implement Research Agent with MCP tools
8. Implement Code Generation Agent
9. Implement Validation Agent
10. Implement Refinement Agent
11. Implement Finalization Agent

### Phase 3: Orchestration
12. ✅ Write all prompts in `prompts/BRAZE_PROMPTS.py` (Already complete from Phase 2)
13. Implement `core/workflow.py` with router **+ streaming support**
14. Implement `agents/braze_code_generator.py` main orchestrator **+ streaming methods**
15. Add Opik tracing

### Phase 4: UI
16. Implement Gradio UI in `ui/gradio_app.py` **+ streaming response handler**
17. Add feature suggestions in `utils/sdk_suggestions.py`
18. Add iframe preview and export functionality
19. **Add real-time progress indicators** (agent status messages, validation loop visibility)
20. Create run script

### Phase 5: Testing & Polish
21. Write unit tests
22. Write integration tests
23. End-to-end manual testing with streaming
24. Bug fixes and refinements

## Success Criteria

- TAM user inputs "I want push notifications and user tracking"
- **User sees real-time progress** as each agent completes (streaming updates)
- System generates single HTML file with:
  - Braze SDK properly initialized
  - Push notification subscription UI
  - User identification form
  - Event tracking examples
  - All working in browser
- File passes Playwright validation (no console errors)
- Preview shows in Gradio iframe
- **Validation loop visible** if refinement needed (up to 3 iterations)
- Total generation time < 2 minutes

## Reference Files

Key files to reference during implementation:
- [code/deep_research/agents/react_multi_agent.py](code/deep_research/agents/react_multi_agent.py) - Architecture pattern
- [code/deep_research/core/chat_interface.py](code/deep_research/core/chat_interface.py) - Interface to implement
- [braze-docs-mcp/server.py](braze-docs-mcp/server.py) - MCP server to integrate
- [code/deep_research/app.py](code/deep_research/app.py) - Gradio UI pattern
- [code/deep_research/prompts/AGENT_PROMPTS.py](code/deep_research/prompts/AGENT_PROMPTS.py) - Prompt structure examples

## Notes

- Use `gpt-4o` for code generation (better at code than gpt-4o-mini)
- Use `temperature=0.3` for more consistent code output
- Cache MCP documentation queries to reduce latency
- Save all generated HTML files with timestamps for debugging
- Log all Playwright errors to help with refinement
