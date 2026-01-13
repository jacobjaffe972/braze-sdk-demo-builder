# Braze SDK Landing Page Generator - UI

This directory contains the Gradio-based web interface for the Braze SDK Landing Page Generator.

## Features

### Three-Section Workflow

The UI is organized into three accordion sections that guide users through the generation process:

#### 1️⃣ Configure Braze API
- Enter Braze API credentials (API key + REST endpoint)
- Validates credentials before proceeding
- Default endpoint pre-populated from environment variables

#### 2️⃣ Generate Landing Page
- **Chat Interface**: Natural language input for feature requests
- **Streaming Updates**: Real-time progress indicators as agents work
- **Quick Suggestions**: Pre-built templates for common use cases
  - 🔔 Push Notifications
  - 📊 User Tracking
  - 💬 In-App Messages
  - 🗂️ Content Cards
  - 👤 User Identification
  - 📧 Email Subscription
  - 📝 User Properties
  - 🎯 Full SDK Demo

#### 3️⃣ Preview & Export
- **Preview Tab**: Live iframe preview of generated landing page
- **Branding Tab**: View extracted branding data (colors, fonts)
- **Download**: Export HTML file for deployment

### Key Capabilities

- **Real-Time Streaming**: Watch the 6-agent workflow execute in real-time
- **Automatic Branding**: Extracts colors and fonts from customer websites
- **Browser Validation**: Optional Playwright testing for code quality
- **Single-File Output**: Self-contained HTML with inline CSS/JS
- **No Login Required**: Fully local, no external authentication

## Usage

### Quick Start

From the repository root:

```bash
./launch_ui.sh
```

Then open http://localhost:7860 in your browser.

### Manual Launch

Using Python directly:

```bash
cd code
python -m braze_code_gen
```

### Advanced Options

```bash
# Custom port
python -m braze_code_gen --port 8080

# Enable public sharing
python -m braze_code_gen --share

# Disable browser testing (faster)
python -m braze_code_gen --no-browser-testing

# Custom export directory
python -m braze_code_gen --export-dir /path/to/exports

# Debug mode
python -m braze_code_gen --debug
```

## Architecture

### Components

- **[gradio_app.py](gradio_app.py)**: Main Gradio interface
  - `BrazeCodeGenUI`: UI wrapper class
  - `create_gradio_interface()`: Builds the three-section UI
  - `launch_ui()`: Launch function with configuration

- **[components.py](components.py)**: Reusable UI components (future)

### Integration Points

The UI integrates with:
- **Orchestrator** ([agents/orchestrator.py](../agents/orchestrator.py)): Coordinates 6-agent workflow
- **Streaming Workflow** ([core/workflow.py](../core/workflow.py)): Provides real-time updates
- **Website Analyzer** ([tools/website_analyzer.py](../tools/website_analyzer.py)): Extracts branding
- **HTML Exporter** ([utils/exporter.py](../utils/exporter.py)): Saves generated files

### Streaming Implementation

The UI uses generator functions to stream updates:

```python
def generate_streaming(message, history):
    """Stream updates as each agent completes."""
    for update in orchestrator.generate_streaming(message):
        if update["type"] == "node_complete":
            # Show status: ✓ Planning complete
            yield updated_history
        elif update["type"] == "message":
            # Show agent message
            yield updated_history
        elif update["type"] == "error":
            # Show error
            yield updated_history
```

This provides transparency into the multi-agent workflow without blocking the UI.

## Environment Variables

Optional environment variables (set in `.env`):

```bash
# Pre-populate API configuration
BRAZE_API_KEY=edc26b45-1538-4a6c-bd3f-3b95ee52d784
BRAZE_SDK_ENDPOINT=sondheim.braze.com

# OpenAI API key (required for LLM calls)
OPENAI_API_KEY=your_openai_key_here
```

## User Flow

1. **User opens UI** → Section 1 (API Configuration) is open
2. **User enters API credentials** → Click "Validate & Continue"
3. **Section 1 closes, Section 2 opens** → Chat interface ready
4. **User enters request** (with optional website URL) → Click "Generate"
5. **Real-time updates stream** → Progress shown with ✓/⚠ indicators
6. **Section 3 opens automatically** → Preview and export available
7. **User previews page** → View in iframe
8. **User downloads HTML** → Click "Prepare Download"

## Development

### Adding New Feature Suggestions

Edit [utils/sdk_suggestions.py](../utils/sdk_suggestions.py):

```python
FEATURE_SUGGESTIONS.append({
    "id": "new_feature",
    "label": "New Feature",
    "description": "Description",
    "prompt": "Full prompt for the feature",
    "features": ["sdkMethod1()", "sdkMethod2()"],
    "icon": "🎯"
})
```

### Customizing UI Theme

In `gradio_app.py`, modify the theme:

```python
with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="cyan")
) as demo:
    # ...
```

Available themes: `gr.themes.Soft()`, `gr.themes.Default()`, `gr.themes.Glass()`, `gr.themes.Monochrome()`

### Testing UI Locally

Test without launching the full server:

```python
from braze_code_gen.ui.gradio_app import BrazeCodeGenUI

ui = BrazeCodeGenUI()
print("UI initialized:", ui.orchestrator is not None)
```

## Troubleshooting

### "Gradio not found"
```bash
pip install gradio>=4.0.0
```

### "Braze API configuration not set"
Make sure to complete Section 1 (API Configuration) before generating.

### "No preview available"
The preview loads after generation completes. Click "Refresh Preview" if needed.

### Port already in use
```bash
python -m braze_code_gen --port 8080
```

### Streaming not working
Ensure you're using a modern browser (Chrome, Firefox, Edge). Safari may have issues with streaming.

## Performance

### Generation Time
- **Planning + Research**: 10-20 seconds
- **Code Generation**: 10-15 seconds
- **Validation**: 5-10 seconds (if browser testing enabled)
- **Total**: 30-60 seconds for complete generation

### Optimization Tips
1. **Disable browser testing** for faster iteration: `--no-browser-testing`
2. **Use faster model** for research: Edit `orchestrator.py` to use `gpt-4o-mini`
3. **Skip website analysis**: Don't include website URLs in requests

## Security Notes

- **API Keys**: Stored in browser memory only, not persisted
- **Generated HTML**: Saved locally to `export_dir`, not uploaded anywhere
- **Website Scraping**: Uses standard HTTP requests with User-Agent headers
- **No External Services**: All processing happens locally (except LLM API calls)

## Future Enhancements

Potential improvements for Phase 5:

- [ ] Token-level streaming (smoother text generation)
- [ ] History persistence (save previous generations)
- [ ] Batch generation (multiple landing pages at once)
- [ ] Template library (save and reuse custom templates)
- [ ] A/B testing mode (generate variations)
- [ ] Direct deployment (push to S3, Netlify, etc.)
- [ ] Collaborative mode (team sharing)

## Support

For issues or questions:
- Check [IMPLEMENTATION_PLAN.md](../../../IMPLEMENTATION_PLAN.md) for architecture details
- Review agent logs in debug mode: `--debug`
- Open an issue on the repository
