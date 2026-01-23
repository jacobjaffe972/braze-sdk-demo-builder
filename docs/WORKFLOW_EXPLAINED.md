# Braze Code Generator - Complete Workflow Explained

This document explains exactly how the multi-agent system works, from user input to final HTML output.

## Table of Contents
- [High-Level Overview](#high-level-overview)
- [State Management](#state-management)
- [Agent-by-Agent Flow](#agent-by-agent-flow)
- [Prompt Variable Flow](#prompt-variable-flow)
- [LLM Invocation Details](#llm-invocation-details)
- [Complete Example Trace](#complete-example-trace)

---

## High-Level Overview

```
User Input: "Build a landing page with user tracking for https://spotify.com"
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    WORKFLOW STATE                            │
│  (Shared dictionary passed between all agents)               │
│  - messages: [HumanMessage(...)]                            │
│  - customer_website_url: None → "https://spotify.com"       │
│  - branding_data: None → BrandingData(...)                  │
│  - feature_plan: None → SDKFeaturePlan(...)                 │
│  - research_results: None → ResearchResults(...)            │
│  - generated_code: None → GeneratedCode(...)                │
│  - validation_results: None → ValidationResults(...)        │
│  - next_step: "planning" → "research" → "code_gen" → ...   │
└─────────────────────────────────────────────────────────────┘
    ↓
[1] Planning Agent
    → Reads: messages
    → Extracts: URL from message
    → Calls: WebsiteAnalyzer (no LLM)
    → LLM Call #1: Create feature plan (structured output)
    → Updates state: customer_website_url, branding_data, feature_plan
    → Sets: next_step = "research"
    ↓
[2] Research Agent
    → Reads: feature_plan
    → LLM Call #2: Analyze features & generate search queries
    → Calls: Braze MCP tools (search_braze_docs, get_code_examples)
    → LLM Call #3: Synthesize research into summary
    → Updates state: research_results
    → Sets: next_step = "code_generation"
    ↓
[3] Code Generation Agent
    → Reads: feature_plan, branding_data, research_results
    → Generates: Base HTML template (no LLM)
    → LLM Call #4: Generate complete HTML with SDK integration
    → Updates state: generated_code
    → Sets: next_step = "validation"
    ↓
[4] Validation Agent
    → Reads: generated_code
    → Calls: Playwright browser test (no LLM)
    → LLM Call #5: Analyze validation results, decide PASS/FAIL
    → Updates state: validation_results
    → Sets: next_step = "refinement" (if FAIL) or "finalization" (if PASS)
    ↓
[5] Refinement Agent (if validation failed, max 3 iterations)
    → Reads: generated_code, validation_results
    → LLM Call #6: Fix identified issues
    → Updates state: generated_code (fixed version)
    → Sets: next_step = "validation" (loop back)
    ↓
[6] Finalization Agent
    → Reads: generated_code, validation_results
    → LLM Call #7: Polish code (comments, formatting, metadata)
    → Updates state: final_code
    → Exports: HTML file + metadata JSON
    ↓
Output: landing_page.html
```

---

## State Management

### The State Object

All agents share a single `CodeGenerationState` dictionary (LangGraph state):

```python
# From code/braze_code_gen/core/state.py
class CodeGenerationState(TypedDict):
    # Core workflow data
    messages: Annotated[list, add_messages]
    customer_website_url: Optional[str]
    branding_data: Optional[BrandingData]
    feature_plan: Optional[SDKFeaturePlan]
    research_results: Optional[ResearchResults]
    generated_code: Optional[GeneratedCode]
    validation_results: Optional[ValidationResults]

    # Workflow control
    next_step: str
    iteration_count: int

    # Configuration
    braze_api_config: BrazeAPIConfig

    # Error handling
    error: Optional[str]
```

### How State Updates Work

Each agent:
1. **Reads** from state (inputs)
2. **Processes** data (with or without LLM)
3. **Returns** a dictionary of updates
4. LangGraph **merges** the updates into shared state
5. Routes to next agent based on `next_step`

```python
# Agent pattern
def process(self, state: CodeGenerationState, config: RunnableConfig) -> dict:
    # Read from state
    user_message = state["messages"][-1].content

    # Do work (LLM calls, tools, etc.)
    result = self._do_work(user_message)

    # Return updates (merged into state)
    return {
        "some_field": result,
        "next_step": "research"
    }
```

---

## Agent-by-Agent Flow

### 🎯 Agent 1: Planning Agent

**File:** `code/braze_code_gen/agents/planning_agent.py`

#### What It Does
1. Extracts website URL from user message (regex)
2. Analyzes website for branding (colors, fonts)
3. Uses LLM to create structured feature plan

#### Input (from state)
```python
{
    "messages": [HumanMessage("Build a page with user tracking for spotify.com")],
    "customer_website_url": None,
    "branding_data": None
}
```

#### Processing Steps

**Step 1: Extract URL** (no LLM)
```python
# planning_agent.py line 114-140
url = self._extract_url_from_message(message)
# Result: "https://spotify.com"
```

**Step 2: Analyze Website** (no LLM, uses requests + BeautifulSoup)
```python
# planning_agent.py line 69
branding_data = self.website_analyzer.analyze_website(url)
# Result: BrandingData(
#   colors=ColorScheme(primary="#1ED760", secondary="#B3B3B3"),
#   typography=TypographyData(primary_font="'Inter', sans-serif")
# )
```

**Step 3: Format Prompt** (no LLM)
```python
# planning_agent.py line 175-179
branding_dict = {
    'primary_color': branding_data.colors.primary,     # "#1ED760"
    'secondary_color': branding_data.colors.secondary, # "#B3B3B3"
    ...
}

prompt = format_planning_agent_prompt(
    user_request=user_message,
    customer_website_url="https://spotify.com",
    branding_data=branding_dict
)
```

**What the prompt looks like after formatting:**
```markdown
You are the Planning Agent for the Braze SDK Landing Page Code Generator.

Your role is to:
1. Analyze the user's feature requests
2. Extract the customer website URL (if provided)
3. Create a comprehensive feature plan with SDK methods
4. Consider customer branding constraints

## Current Context

**User Request**: Build a page with user tracking for spotify.com

**Customer Website URL**: https://spotify.com

## Customer Branding

**Colors**:
- Primary: #1ED760
- Secondary: #B3B3B3
- Accent: #FFFFFF
- Background: #191414
- Text: #FFFFFF

**Typography**:
- Primary Font: 'Inter', sans-serif
- Heading Font: 'Inter', sans-serif

**Extraction Status**: Successfully extracted

## Your Task

Create a detailed feature plan that includes:
1. **List of Features**: Extract all Braze SDK features the user wants
2. **Page Title**: Generate an appropriate landing page title
...
```

**Step 4: LLM Call #1** - Generate Feature Plan
```python
# planning_agent.py line 182-190
messages = [
    SystemMessage(content=prompt),  # Formatted above
    HumanMessage(content="Create the feature plan based on the user request.")
]

response = self.llm.with_structured_output(SDKFeaturePlan).invoke(messages, config)
```

**LLM Configuration:**
- Model: Claude 3.5 Sonnet (via `create_llm(tier=ModelTier.PRIMARY)`)
- Temperature: 0.3 (deterministic)
- Output: **Structured** (Pydantic model `SDKFeaturePlan`)

**LLM Returns (structured):**
```python
SDKFeaturePlan(
    features=[
        SDKFeature(
            name="User Event Tracking",
            description="Track user interactions with custom events",
            sdk_methods=["braze.logCustomEvent(eventName, properties)"],
            implementation_notes="Add tracking to button clicks and form submissions",
            priority=1
        ),
        SDKFeature(
            name="User Identification",
            description="Identify users with changeUser",
            sdk_methods=["braze.changeUser(userId)"],
            implementation_notes="Add user ID input form",
            priority=1
        )
    ],
    page_title="Spotify Braze SDK Demo",
    page_description="Interactive demonstration of Braze SDK features",
    branding_constraints="Use Spotify's green (#1ED760) as primary color"
)
```

#### Output (state updates)
```python
return {
    "customer_website_url": "https://spotify.com",
    "branding_data": branding_data,  # BrandingData object
    "feature_plan": feature_plan,     # SDKFeaturePlan object
    "next_step": "research"
}
```

---

### 🔍 Agent 2: Research Agent

**File:** `code/braze_code_gen/agents/research_agent.py`

#### What It Does
1. Reads feature plan from state
2. Uses LLM to generate search queries for each feature
3. Calls Braze MCP tools to fetch documentation
4. Uses LLM to synthesize findings into implementation guide

#### Input (from state)
```python
{
    "feature_plan": SDKFeaturePlan(...),  # From Planning Agent
    "branding_data": BrandingData(...)
}
```

#### Processing Steps

**Step 1: Format Initial Prompt** (no LLM)
```python
# research_agent.py
prompt = RESEARCH_AGENT_PROMPT.format(
    feature_plan=self._format_feature_plan(feature_plan)
)
```

**Formatted prompt:**
```markdown
You are the Research Agent for the Braze SDK Landing Page Code Generator.

Your role is to research Braze documentation to find implementation guidance.

## Feature Plan

**Page**: Spotify Braze SDK Demo
**Description**: Interactive demonstration of Braze SDK features

**Features to Implement:**

1. **User Event Tracking**
   Description: Track user interactions with custom events
   SDK Methods: braze.logCustomEvent(eventName, properties)
   Notes: Add tracking to button clicks and form submissions
   Priority: 1

2. **User Identification**
   Description: Identify users with changeUser
   SDK Methods: braze.changeUser(userId)
   Notes: Add user ID input form
   Priority: 1

## Your Task

For each feature, use a two-step approach:
- Use `search_braze_docs()` to find documentation
- Use `get_braze_code_examples()` to get implementation code
...
```

**Step 2: LLM Call #2** - Agent with Tool Calling
```python
# research_agent.py - LLM with MCP tools
messages = [
    SystemMessage(content=prompt),
    HumanMessage(content="Research each feature and provide implementation guidance.")
]

# LLM is bound with MCP tools
response = self.llm_with_tools.invoke(messages, config)
```

**LLM Configuration:**
- Model: Claude 3.5 Sonnet
- Temperature: 0.4
- Tools: `search_braze_docs`, `get_braze_code_examples`, `get_braze_event_schema`

**What happens inside this LLM call:**

The LLM makes **multiple tool calls** in a loop:

```
LLM thinks: "I need to research logCustomEvent"
    ↓
LLM returns: tool_use(search_braze_docs, query="logCustomEvent track events")
    ↓
Tool executes → Returns documentation snippets
    ↓
LLM receives tool result
    ↓
LLM thinks: "Now I need code examples"
    ↓
LLM returns: tool_use(get_braze_code_examples, topic="user_tracking")
    ↓
Tool executes → Returns code examples
    ↓
LLM receives tool result
    ↓
LLM thinks: "I have enough info for feature 1, moving to feature 2..."
    ↓
[Repeats for changeUser]
    ↓
LLM returns: Final text response with all research compiled
```

**Step 3: LLM Call #3** - Synthesize Research
```python
# After tool calls complete, format findings into structured summary
synthesis_prompt = f"""
Based on your research, create a structured summary with:
- Code examples for each feature
- Implementation guidance
- Prerequisites

Research findings:
{response.content}
"""

summary = self.llm.with_structured_output(ResearchResults).invoke([
    SystemMessage(content=synthesis_prompt)
])
```

**LLM Returns (structured):**
```python
ResearchResults(
    summary="""
    ## User Event Tracking
    - Method: braze.logCustomEvent(eventName, properties)
    - Example: braze.logCustomEvent('button_clicked', {location: 'header'})
    - Prerequisites: SDK must be initialized first

    ## User Identification
    - Method: braze.changeUser(userId)
    - Example: braze.changeUser('user_12345')
    - Prerequisites: Call before logging events
    """,
    code_examples=[
        "braze.logCustomEvent('page_view', {page: 'home'});",
        "braze.changeUser(document.getElementById('userId').value);"
    ],
    documentation_urls=[
        "https://www.braze.com/docs/developer_guide/platform_integration_guides/web/analytics/tracking_custom_events/",
        "https://www.braze.com/docs/developer_guide/platform_integration_guides/web/analytics/setting_user_ids/"
    ]
)
```

#### Output (state updates)
```python
return {
    "research_results": research_results,  # ResearchResults object
    "next_step": "code_generation"
}
```

---

### 💻 Agent 3: Code Generation Agent

**File:** `code/braze_code_gen/agents/code_generation_agent.py`

#### What It Does
1. Generates base HTML template (no LLM)
2. Formats prompt with all context
3. Uses LLM to generate complete HTML with Braze SDK integration

#### Input (from state)
```python
{
    "feature_plan": SDKFeaturePlan(...),
    "branding_data": BrandingData(...),
    "research_results": ResearchResults(...),
    "braze_api_config": BrazeAPIConfig(api_key="...", sdk_endpoint="...")
}
```

#### Processing Steps

**Step 1: Generate Base Template** (no LLM)
```python
# code_generation_agent.py line 66-71
base_template = generate_base_template(
    branding=branding_data,
    braze_config=braze_config,
    page_title="Spotify Braze SDK Demo",
    page_description="Interactive demonstration..."
)
```

**Base template includes:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Braze SDK Demo</title>
    <style>
        :root {
            --primary-color: #1ED760;
            --secondary-color: #B3B3B3;
            --accent-color: #FFFFFF;
        }
        /* ... CSS with customer branding ... */
    </style>
    <script src="https://js.appboycdn.com/web-sdk/5.4/braze.min.js"></script>
</head>
<body>
    <div id="app"></div>
    <script>
        // SDK Initialization (REAL API KEY)
        braze.initialize('YOUR_ACTUAL_API_KEY', {
            baseUrl: 'sdk.iad-01.braze.com'
        });
        braze.openSession();

        // App initialization will go here
    </script>
</body>
</html>
```

**Step 2: Format Prompt** (no LLM)
```python
# code_generation_agent.py line 81-90
prompt = CODE_GENERATION_AGENT_PROMPT.format(
    feature_plan=self._format_feature_plan(feature_plan),
    research_summary=research_results.summary,
    primary_color=branding_data.colors.primary,      # "#1ED760"
    accent_color=branding_data.colors.accent,        # "#FFFFFF"
    primary_font=branding_data.typography.primary_font,
    heading_font=branding_data.typography.heading_font,
    base_template="[Base template description...]",
    sdk_reference_examples=SDK_REFERENCE_EXAMPLES
)
```

**Formatted prompt (truncated):**
```markdown
You are the Code Generation Agent for the Braze SDK Landing Page Code Generator.

Your role is to generate a complete, functional HTML landing page.

## Feature Plan

**Page**: Spotify Braze SDK Demo
**Description**: Interactive demonstration of Braze SDK features

**Features to Implement:**
1. **User Event Tracking**
   SDK Methods: braze.logCustomEvent(eventName, properties)
   Priority: 1
...

## Research Results

## User Event Tracking
- Method: braze.logCustomEvent(eventName, properties)
- Example: braze.logCustomEvent('button_clicked', {location: 'header'})
...

## Customer Branding

**Colors**: Primary=#1ED760, Accent=#FFFFFF
**Fonts**: Primary='Inter', sans-serif, Heading='Inter', sans-serif

## Base Template

You will build upon this base template:
[Base template is included in the HumanMessage]

## SDK Implementation Reference

The following patterns show correct Braze Web SDK usage:
```javascript
// User Identification
braze.changeUser('user_123');

// Event Tracking
braze.logCustomEvent('button_clicked', {
    button_name: 'signup',
    location: 'header'
});
```
...

## Your Task

Generate a complete HTML file that:
1. Uses Modern JavaScript Architecture (IIFE pattern)
2. Uses Customer Branding (Spotify green #1ED760)
3. Implements All Features
...
```

**Step 3: LLM Call #4** - Generate Complete HTML
```python
# code_generation_agent.py line 94-100
messages = [
    SystemMessage(content=prompt),
    HumanMessage(content=f"Generate the complete HTML landing page.\n\nBase template:\n{base_template}")
]

response = self.llm.invoke(messages, config)
html_content = response.content
```

**LLM Configuration:**
- Model: Claude 3.5 Sonnet
- Temperature: 0.7 (creative)
- Output: **Text** (raw HTML)

**LLM Returns:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify Braze SDK Demo</title>
    <style>
        :root {
            --primary-color: #1ED760;
            --secondary-color: #B3B3B3;
        }
        /* Modern CSS with customer branding */
        body { background: #191414; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        .btn-primary { background: var(--primary-color); }
    </style>
    <script src="https://js.appboycdn.com/web-sdk/5.4/braze.min.js"></script>
</head>
<body>
    <div id="app"></div>

    <script>
        // Braze SDK Initialization
        braze.initialize('YOUR_ACTUAL_API_KEY', {
            baseUrl: 'sdk.iad-01.braze.com'
        });
        braze.openSession();

        // Main App - IIFE Pattern
        window.SpotifyBrazeDemo = (function() {
            const components = {
                button(config) {
                    const { text, id, className = 'btn-primary' } = config;
                    return `<button id="${id}" class="btn ${className}">${text}</button>`;
                },

                formGroup(config) {
                    const { label, id, type = 'text' } = config;
                    return `
                        <div class="form-group">
                            <label>${label}</label>
                            <input type="${type}" id="${id}" class="form-input">
                        </div>
                    `;
                }
            };

            const sections = {
                userTracking() {
                    return `
                        <div class="section-card">
                            <h2>Event Tracking</h2>
                            ${components.button({
                                text: 'Track Event',
                                id: 'trackEventBtn'
                            })}
                        </div>
                    `;
                },

                userIdentification() {
                    return `
                        <div class="section-card">
                            <h2>User Identification</h2>
                            ${components.formGroup({
                                label: 'User ID',
                                id: 'userIdInput'
                            })}
                            ${components.button({
                                text: 'Set User ID',
                                id: 'setUserBtn'
                            })}
                        </div>
                    `;
                }
            };

            const handlers = {
                setupEventTracking() {
                    document.getElementById('trackEventBtn').addEventListener('click', () => {
                        braze.logCustomEvent('button_clicked', {
                            button_name: 'track_event',
                            timestamp: new Date().toISOString()
                        });
                        alert('Event tracked!');
                    });
                },

                setupUserIdentification() {
                    document.getElementById('setUserBtn').addEventListener('click', () => {
                        const userId = document.getElementById('userIdInput').value;
                        if (userId) {
                            braze.changeUser(userId);
                            alert(`User ID set to: ${userId}`);
                        }
                    });
                }
            };

            function init() {
                // Render UI
                const app = document.getElementById('app');
                app.innerHTML = `
                    <div class="container">
                        <h1>Spotify Braze SDK Demo</h1>
                        ${sections.userTracking()}
                        ${sections.userIdentification()}
                    </div>
                `;

                // Setup handlers
                handlers.setupEventTracking();
                handlers.setupUserIdentification();
            }

            return { init };
        })();

        // Initialize app after DOM loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', SpotifyBrazeDemo.init);
        } else {
            SpotifyBrazeDemo.init();
        }
    </script>
</body>
</html>
```

**Step 4: Clean & Package** (no LLM)
```python
# code_generation_agent.py line 104
html_content = clean_html_response(html_content)  # Remove markdown code blocks if present

generated_code = GeneratedCode(
    html=html_content,
    braze_sdk_initialized=True,
    features_implemented=["User Event Tracking", "User Identification"]
)
```

#### Output (state updates)
```python
return {
    "generated_code": generated_code,
    "next_step": "validation"
}
```

---

### ✅ Agent 4: Validation Agent

**File:** `code/braze_code_gen/agents/validation_agent.py`

#### What It Does
1. Tests HTML in headless browser (Playwright)
2. Uses LLM to analyze test results and decide PASS/FAIL

#### Input (from state)
```python
{
    "generated_code": GeneratedCode(html="<!DOCTYPE html>...")
}
```

#### Processing Steps

**Step 1: Browser Testing** (no LLM)
```python
# validation_agent.py - uses Playwright
validation_report = self.browser_tester.test_page(generated_code.html)
```

**What browser testing does:**
```python
# Launches headless Chromium
# Loads HTML in browser
# Checks:
#   - Page loads without errors
#   - Braze SDK script loads
#   - braze object is defined
#   - No JavaScript console errors
#   - Forms and buttons render
# Returns: TestReport with results
```

**Test report:**
```python
{
    "page_loaded": True,
    "braze_sdk_loaded": True,
    "javascript_errors": [],
    "console_warnings": ["Deprecated API usage"],
    "elements_found": ["#trackEventBtn", "#setUserBtn", "#userIdInput"],
    "elements_missing": [],
    "screenshot": "base64_encoded_image"
}
```

**Step 2: Format Prompt** (no LLM)
```python
# validation_agent.py
prompt = VALIDATION_AGENT_PROMPT.format(
    generated_code_summary=f"Generated {len(generated_code.html)} chars",
    validation_report=self._format_report(validation_report)
)
```

**Formatted prompt:**
```markdown
You are the Validation Agent for the Braze SDK Landing Page Code Generator.

Your role is to review the validation report and determine if code is ready.

## Generated Code

Generated 15432 characters of HTML

## Validation Report

**Page Load**: ✓ Success
**Braze SDK**: ✓ Loaded
**JavaScript Errors**: None
**Console Warnings**: 1 warning
  - Deprecated API usage

**Elements Found**: 3
  - #trackEventBtn
  - #setUserBtn
  - #userIdInput

**Elements Missing**: None

## Your Task

Analyze the report and determine:
1. Critical Issues (prevent deployment)
2. Important Issues (affect functionality)
3. Minor Issues (affect quality)

## Decision Criteria

**Pass**: All critical checks pass
**Fail**: Any critical issue present
...
```

**Step 3: LLM Call #5** - Analyze & Decide
```python
# validation_agent.py
messages = [
    SystemMessage(content=prompt),
    HumanMessage(content="Analyze the validation report and make a decision.")
]

response = self.llm.with_structured_output(ValidationDecision).invoke(messages)
```

**LLM Configuration:**
- Model: Claude 3.5 Haiku (faster, cheaper for validation)
- Temperature: 0.2 (deterministic)
- Output: **Structured** (Pydantic model)

**LLM Returns (structured):**
```python
ValidationDecision(
    decision="PASS",
    critical_issues=[],
    recommendations=[
        "Fix deprecated API warning",
        "Add loading indicators"
    ],
    priority="LOW"
)
```

#### Output (state updates)
```python
return {
    "validation_results": ValidationResults(
        passed=True,
        issues=[],
        recommendations=["Fix deprecated API warning"],
        test_report=validation_report
    ),
    "next_step": "finalization"  # or "refinement" if failed
}
```

---

### 🔧 Agent 5: Refinement Agent (if validation failed)

**File:** `code/braze_code_gen/agents/refinement_agent.py`

#### What It Does
1. Reads validation issues
2. Uses LLM to apply targeted fixes
3. Preserves working code

**Only runs if validation fails. Max 3 iterations.**

#### Input (from state)
```python
{
    "generated_code": GeneratedCode(...),
    "validation_results": ValidationResults(
        passed=False,
        issues=["Braze SDK not initialized", "Button click handler broken"]
    ),
    "iteration_count": 1
}
```

#### Processing Steps

**Step 1: Format Prompt**
```python
prompt = REFINEMENT_AGENT_PROMPT.format(
    original_code_summary="15432 chars",
    validation_issues="SDK not initialized, handler broken",
    issues_to_fix=validation_results.issues
)
```

**Step 2: LLM Call #6** - Fix Issues
```python
messages = [
    SystemMessage(content=prompt),
    HumanMessage(content=f"Fix these issues:\n{issues}\n\nOriginal code:\n{html}")
]

response = self.llm.invoke(messages)
fixed_html = clean_html_response(response.content)
```

**LLM Configuration:**
- Model: Claude 3.5 Sonnet
- Temperature: 0.5
- Output: **Text** (fixed HTML)

#### Output (state updates)
```python
return {
    "generated_code": GeneratedCode(html=fixed_html, ...),
    "iteration_count": iteration_count + 1,
    "next_step": "validation"  # Loop back
}
```

---

### ✨ Agent 6: Finalization Agent

**File:** `code/braze_code_gen/agents/finalization_agent.py`

#### What It Does
1. Uses LLM to polish code (comments, formatting)
2. Adds metadata and documentation
3. Exports final HTML

#### Input (from state)
```python
{
    "generated_code": GeneratedCode(...),
    "validation_results": ValidationResults(passed=True)
}
```

#### Processing Steps

**Step 1: Format Prompt**
```python
prompt = FINALIZATION_AGENT_PROMPT.format(
    final_code_summary="Validated, ready to polish",
    validation_status="PASSED"
)
```

**Step 2: LLM Call #7** - Polish
```python
messages = [
    SystemMessage(content=prompt),
    HumanMessage(content=f"Polish this code:\n{html}")
]

response = self.llm.invoke(messages)
polished_html = clean_html_response(response.content)
```

**LLM adds:**
- JSDoc comments
- HTML comment header with usage instructions
- Meta tags for SEO
- Cleans up console.log statements

#### Output
```python
# Exports to file
output_path = "outputs/spotify_demo.html"
with open(output_path, 'w') as f:
    f.write(polished_html)

# Also creates metadata JSON
metadata = {
    "customer": "Spotify",
    "features": ["User Event Tracking", "User Identification"],
    "branding": {...},
    "generated_at": "2026-01-23T14:30:00Z"
}
```

---

## Prompt Variable Flow

### Variable Lifecycle

```
User Input: "Build a page for spotify.com"
    ↓
[Planning Agent]
├─ Extracts: customer_website_url = "https://spotify.com"
├─ Analyzes: branding_data = BrandingData(colors=ColorScheme(...))
├─ Variable: primary_color = branding_data.colors.primary
│            → Value: "#1ED760"
├─ Formats:  PLANNING_AGENT_PROMPT.format(
│              user_request="Build a page for spotify.com",
│              customer_website_url="https://spotify.com",
│              branding_section=PLANNING_AGENT_BRANDING_SECTION.format(
│                  primary_color="#1ED760",
│                  secondary_color="#B3B3B3",
│                  ...
│              )
│            )
└─ LLM sees: Fully formatted prompt with actual values

State Updated:
{
    "customer_website_url": "https://spotify.com",
    "branding_data": BrandingData(colors=ColorScheme(primary="#1ED760")),
    "feature_plan": SDKFeaturePlan(...)
}
    ↓
[Code Generation Agent]
├─ Reads:    primary_color = state["branding_data"].colors.primary
│            → Value: "#1ED760"
├─ Formats:  CODE_GENERATION_AGENT_PROMPT.format(
│              primary_color="#1ED760",
│              feature_plan=formatted_plan,
│              ...
│            )
└─ LLM sees: "Use customer branding: Primary=#1ED760"

Generated HTML contains:
<style>
    :root {
        --primary-color: #1ED760;  /* Injected from branding_data */
    }
</style>
```

### Example: How `{primary_color}` Flows

```python
# Step 1: Website Analysis (Planning Agent)
branding_data = WebsiteAnalyzer().analyze_website("https://spotify.com")
# branding_data.colors.primary = "#1ED760"

# Step 2: Store in State
state["branding_data"] = branding_data

# Step 3: Planning Agent Prompt Formatting
branding_dict = {
    'primary_color': branding_data.colors.primary  # "#1ED760"
}
branding_section = PLANNING_AGENT_BRANDING_SECTION.format(
    primary_color=branding_dict['primary_color']  # "#1ED760"
)
# Result: "**Colors**:\n- Primary: #1ED760"

# Step 4: Code Gen Agent Reads from State
primary_color = state["branding_data"].colors.primary  # "#1ED760"

# Step 5: Code Gen Prompt Formatting
prompt = CODE_GENERATION_AGENT_PROMPT.format(
    primary_color=primary_color  # "#1ED760"
)
# Result: "**Colors**: Primary=#1ED760, Accent=#FFFFFF"

# Step 6: LLM Generates HTML
# LLM sees: "Use Primary=#1ED760"
# LLM writes: "--primary-color: #1ED760;"
```

---

## LLM Invocation Details

### Summary of All LLM Calls

| # | Agent | Purpose | Model | Temp | Output Type | Tools |
|---|-------|---------|-------|------|-------------|-------|
| 1 | Planning | Create feature plan | Sonnet 4.5 | 0.3 | Structured (SDKFeaturePlan) | None |
| 2 | Research | Generate search queries | Sonnet 4.5 | 0.4 | Text + Tool calls | MCP tools |
| 3 | Research | Synthesize findings | Sonnet 4.5 | 0.4 | Structured (ResearchResults) | None |
| 4 | Code Gen | Generate HTML | Sonnet 4.5 | 0.7 | Text (HTML) | None |
| 5 | Validation | Analyze test results | Haiku 3.5 | 0.2 | Structured (ValidationDecision) | None |
| 6 | Refinement | Fix issues | Sonnet 4.5 | 0.5 | Text (HTML) | None |
| 7 | Finalization | Polish code | Sonnet 4.5 | 0.6 | Text (HTML) | None |

### LLM Configuration Details

```python
# From code/braze_code_gen/core/llm_factory.py

def create_llm(tier: ModelTier, temperature: float):
    if tier == ModelTier.PRIMARY:
        # Used by: Planning, Code Gen, Refinement, Finalization
        model = "claude-sonnet-4-5-20250929"

    elif tier == ModelTier.RESEARCH:
        # Used by: Research (with tools)
        model = "claude-sonnet-4-5-20250929"

    elif tier == ModelTier.VALIDATION:
        # Used by: Validation (cheaper, faster)
        model = "claude-3-5-haiku-20241022"

    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=8192,
        streaming=True  # Enables token streaming via callbacks
    )
```

### Structured Output vs Text Output

**Structured Output (Pydantic models):**
```python
# Agent defines expected structure
class SDKFeaturePlan(BaseModel):
    features: List[SDKFeature]
    page_title: str
    page_description: str

# LLM invocation
response = llm.with_structured_output(SDKFeaturePlan).invoke(messages)
# Returns: SDKFeaturePlan(features=[...], page_title="...", ...)
# Type-safe, validated
```

**Text Output (raw HTML/markdown):**
```python
# LLM invocation
response = llm.invoke(messages)
html = response.content
# Returns: string (raw HTML)
# Manual parsing/cleaning needed
```

---

## Complete Example Trace

Let's trace one complete execution with actual values:

### User Input
```
"Build a landing page with user tracking and email capture for spotify.com"
```

### Initial State
```python
{
    "messages": [HumanMessage(content="Build a landing page...")],
    "customer_website_url": None,
    "branding_data": None,
    "feature_plan": None,
    "research_results": None,
    "generated_code": None,
    "validation_results": None,
    "next_step": "planning",
    "iteration_count": 0,
    "braze_api_config": BrazeAPIConfig(
        api_key="abc123",
        sdk_endpoint="sdk.iad-01.braze.com"
    )
}
```

---

### 🎯 Planning Agent Execution

**Reads from state:**
```python
user_message = state["messages"][-1].content
# "Build a landing page with user tracking and email capture for spotify.com"
```

**Extracts URL (regex):**
```python
customer_website_url = "https://spotify.com"
```

**Analyzes website (HTTP + CSS parsing):**
```python
branding_data = BrandingData(
    website_url="https://spotify.com",
    colors=ColorScheme(
        primary="#1ED760",
        secondary="#B3B3B3",
        accent="#FFFFFF",
        background="#191414",
        text="#FFFFFF"
    ),
    typography=TypographyData(
        primary_font="'Inter', sans-serif",
        heading_font="'Inter', sans-serif"
    ),
    extraction_success=True
)
```

**Formats prompt:**
```python
# Nested formatting
branding_section = PLANNING_AGENT_BRANDING_SECTION.format(
    primary_color="#1ED760",
    secondary_color="#B3B3B3",
    accent_color="#FFFFFF",
    background_color="#191414",
    text_color="#FFFFFF",
    primary_font="'Inter', sans-serif",
    heading_font="'Inter', sans-serif",
    extraction_status="Successfully extracted"
)
# Result: "## Customer Branding\n**Colors**:\n- Primary: #1ED760\n..."

full_prompt = PLANNING_AGENT_PROMPT.format(
    user_request="Build a landing page with user tracking...",
    customer_website_url="https://spotify.com",
    branding_section=branding_section,
    branding_constraints="Use Spotify's colors and fonts"
)
```

**LLM Call #1:**
```python
messages = [
    SystemMessage(content=full_prompt),
    HumanMessage(content="Create the feature plan.")
]

response = llm.with_structured_output(SDKFeaturePlan).invoke(messages)
```

**LLM returns:**
```python
feature_plan = SDKFeaturePlan(
    features=[
        SDKFeature(
            name="User Event Tracking",
            description="Track user interactions",
            sdk_methods=["braze.logCustomEvent(eventName, properties)"],
            implementation_notes="Add click tracking to buttons",
            priority=1
        ),
        SDKFeature(
            name="Email Capture",
            description="Collect user email addresses",
            sdk_methods=["braze.getUser().setEmail(email)"],
            implementation_notes="Create email input form",
            priority=1
        )
    ],
    page_title="Spotify Braze SDK Demo",
    page_description="Interactive SDK demonstration with user tracking",
    branding_constraints="Use Spotify green (#1ED760) and dark theme"
)
```

**Updates state:**
```python
{
    "customer_website_url": "https://spotify.com",
    "branding_data": branding_data,
    "feature_plan": feature_plan,
    "next_step": "research"
}
```

---

### 🔍 Research Agent Execution

**Reads from state:**
```python
feature_plan = state["feature_plan"]
# SDKFeaturePlan(features=[...])
```

**LLM Call #2 (with tools):**
```
LLM receives prompt → Thinks → Calls tool: search_braze_docs("logCustomEvent")
    ↓
Tool returns docs → LLM processes → Calls tool: get_braze_code_examples("user_tracking")
    ↓
Tool returns code → LLM processes → Calls tool: search_braze_docs("setEmail")
    ↓
Tool returns docs → LLM has all info → Returns final response
```

**LLM Call #3 (synthesis):**
```python
research_results = ResearchResults(
    summary="## Feature Implementation Guide\n\n### User Event Tracking\n...",
    code_examples=["braze.logCustomEvent('click', {btn: 'cta'});"],
    documentation_urls=["https://braze.com/docs/..."]
)
```

**Updates state:**
```python
{
    "research_results": research_results,
    "next_step": "code_generation"
}
```

---

### 💻 Code Generation Agent Execution

**Reads from state:**
```python
feature_plan = state["feature_plan"]
branding_data = state["branding_data"]
research_results = state["research_results"]
braze_config = state["braze_api_config"]
```

**Generates base template:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Braze SDK Demo</title>
    <style>
        :root {
            --primary-color: #1ED760;
            --bg-color: #191414;
        }
    </style>
    <script src="https://js.appboycdn.com/web-sdk/5.4/braze.min.js"></script>
</head>
<body>
    <div id="app"></div>
    <script>
        braze.initialize('abc123', {baseUrl: 'sdk.iad-01.braze.com'});
        braze.openSession();
    </script>
</body>
</html>
```

**LLM Call #4:**
```
Input: Base template + Feature plan + Research + Branding
Output: Complete HTML (5000+ lines)
```

**Updates state:**
```python
{
    "generated_code": GeneratedCode(html="<!DOCTYPE html>..."),
    "next_step": "validation"
}
```

---

### ✅ Validation Agent Execution

**Browser test:**
```
Launch Chromium → Load HTML → Check SDK → Check errors → Take screenshot
Result: PASS (all checks successful)
```

**LLM Call #5:**
```python
# Analyzes test report
decision = ValidationDecision(decision="PASS", critical_issues=[])
```

**Updates state:**
```python
{
    "validation_results": ValidationResults(passed=True),
    "next_step": "finalization"
}
```

---

### ✨ Finalization Agent Execution

**LLM Call #7:**
```
Input: Generated HTML
Output: Polished HTML with comments and metadata
```

**Exports:**
```
outputs/spotify_demo.html
outputs/spotify_demo_metadata.json
```

---

## Key Takeaways

1. **State is the source of truth** - All data flows through the shared state dictionary
2. **Prompts are templates** - Variables are injected using `.format()` with actual data
3. **7 LLM calls total** - Each serves a specific purpose (plan, research, generate, validate, fix, polish)
4. **Structured output for data** - Uses Pydantic models when extracting information
5. **Text output for code** - Uses raw text when generating HTML/CSS/JS
6. **Agent handoffs are explicit** - Each agent sets `next_step` to route to next agent
7. **Data flows forward** - Each agent adds to state, rarely modifies existing data

