# Braze SDK Landing Page Generator

Generate branded, production-ready landing pages with working Braze SDK integrations — just from a URL and a prompt.

---

## How It Works

Describe what you want, provide a customer website URL, and six AI agents handle the rest:

```
User Input: "Build a landing page with user tracking for https://spotify.com"
    |
┌─────────────────────────────────────────────────────────────┐
│                      WORKFLOW STATE                          │
│  (Shared dictionary passed between all agents)              │
│                                                             │
│  - messages:            [HumanMessage(...)]                 │
│  - customer_website_url: None -> "https://spotify.com"      │
│  - branding_data:        None -> BrandingData(...)          │
│  - feature_plan:         None -> SDKFeaturePlan(...)        │
│  - research_results:     None -> ResearchResults(...)       │
│  - generated_code:       None -> GeneratedCode(...)         │
│  - validation_results:   None -> ValidationResults(...)     │
│  - next_step:           "planning" -> "research" -> ...     │
└─────────────────────────────────────────────────────────────┘
    |
[1] Planning Agent
    - Reads: messages
    - Extracts URL, scrapes website for branding (colors, fonts)
    - Uses LLM to create structured feature plan with SDK methods
    - Updates state: customer_website_url, branding_data, feature_plan
    - Sets: next_step = "research"
    |
[2] Research Agent
    - Reads: feature_plan
    - Calls Braze MCP tools (search_docs, get_code_examples)
    - Synthesizes findings into implementation guide
    - Updates state: research_results
    - Sets: next_step = "code_generation"
    |
[3] Code Generation Agent
    - Reads: feature_plan, branding_data, research_results
    - Generates base HTML template with customer branding
    - Uses LLM to produce complete page with SDK integration
    - Updates state: generated_code
    - Sets: next_step = "validation"
    |
[4] Validation Agent
    - Reads: generated_code
    - Launches headless browser (Playwright)
    - Checks: page loads, SDK initializes, no JS errors
    - Updates state: validation_results
    |
    |--- FAIL? ---> [5] Refinement Agent (max 3 iterations)
    |                    - Reads: generated_code, validation_results
    |                    - Applies targeted fixes, preserves working code
    |                    - Updates state: generated_code (fixed)
    |                    - Loops back to Validation
    |
    |--- PASS? ---> [6] Finalization Agent
                         - Reads: generated_code, validation_results
                         - Polishes code, adds comments and metadata
                         - Exports: HTML file + JSON metadata
    |
Output: landing_page.html
```

---

## Getting Started

### 1. Configure Your API Keys

Ensure your local .env file includes:

- **LLM API Key** — OpenAI, Anthropic, or Google (depending on your configured provider)
- **Braze API Key** — Your Braze REST API key
- **Braze SDK Endpoint** — Your instance endpoint (e.g. `sondheim.braze.com`)

### 2. Send a Prompt

Try something like:

> *"Build a landing page with email capture and push notification opt-in for https://nike.com"*

> *"Create a product launch page with user tracking for https://spotify.com"*

The system will stream progress updates as each agent completes its work.

### 3. Download Your Page

Once complete, you'll receive a self-contained HTML file — ready to open in a browser or deploy.

---

## Tips

- **Include a URL** in your message so the Planning agent can extract real branding from the site
- **Be specific about features** you want (email capture, push notifications, event tracking, etc.)
- The generated page is a **single HTML file** with all CSS and JS inline — no external dependencies beyond the Braze SDK
- If validation fails, the system automatically attempts to fix issues before finalizing
