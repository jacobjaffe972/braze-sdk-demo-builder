# Braze SDK Landing Page Generator - UI

This directory contains the Chainlit-based chat interface for the Braze SDK Landing Page Generator.

## Architecture

The UI is built on [Chainlit](https://chainlit.io/) and uses a chat-based interaction model with per-agent **Steps** for real-time progress visibility.

### Components

- **[chainlit_app.py](../chainlit_app.py)**: Main Chainlit application
  - `on_chat_start`: Session init, API credential collection (or auto-load from `.env`)
  - `on_message`: Runs the 6-agent workflow with streaming Steps
  - `on_stop`: Handles the stop-generation action

- **[chainlit_callbacks.py](chainlit_callbacks.py)**: LangChain callback handler
  - `ChainlitTokenCallbackHandler`: Routes LLM tokens from the sync LangChain thread into the async Chainlit side via a thread-safe queue

- **[assets/](assets/)**: Static assets (Braze logo)

### Configuration

Chainlit config lives at `code/.chainlit/config.toml`. Custom CSS and the Braze logo are served from `code/public/`.

### Streaming Strategy

LangGraph's `graph.stream()` only yields chunks after each node finishes. To get real-time token streaming, the UI:

1. Opens a Chainlit Step **proactively** before each node starts
2. Predicts the next node when the current one completes
3. Drains a thread-safe `Queue` of tokens into the active Step via `stream_token()`

This gives smooth, live output while preserving the collapsible per-agent Step structure.

## Integration Points

- **Orchestrator** ([agents/orchestrator.py](../agents/orchestrator.py)): Coordinates the 6-agent workflow
- **Streaming Workflow** ([core/workflow.py](../core/workflow.py)): Provides real-time updates
- **Website Analyzer** ([tools/website_analyzer.py](../tools/website_analyzer.py)): Extracts branding
- **HTML Exporter** ([utils/exporter.py](../utils/exporter.py)): Saves generated files

## User Flow

1. **Chat opens** -> Credentials loaded from `.env` or prompted interactively
2. **User sends prompt** (with optional website URL) -> Workflow starts
3. **Per-agent Steps** expand/collapse with live token streaming
4. **Completion** -> Download link for the HTML file appears in chat
5. **Stop button** -> Cancels generation mid-stream via `threading.Event`

## Launch

```bash
# From repository root
./launch.sh

# Custom port
./launch.sh 8080
```

Default URL: http://localhost:7800

## Environment Variables

```bash
# Pre-populate API configuration (skip interactive prompts)
BRAZE_API_KEY=your_braze_api_key
BRAZE_SDK_ENDPOINT=sondheim.braze.com

# LLM provider
MODEL_PROVIDER=openai  # or anthropic, google
OPENAI_API_KEY=sk-...
```

## Security Notes

- **API Keys**: Stored in Chainlit session memory only, not persisted to disk
- **Generated HTML**: Saved locally to the export directory, not uploaded anywhere
- **No External Services**: All processing is local (except LLM API calls)
