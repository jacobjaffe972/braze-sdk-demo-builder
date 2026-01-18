"""Braze Code Gen UI package."""

# Lazy imports to avoid dependency issues
__all__ = ["BrazeTheme", "create_gradio_interface", "launch_ui"]


def __getattr__(name):
    """Lazy import of UI components."""
    if name == "BrazeTheme":
        from braze_code_gen.ui.theme import BrazeTheme
        return BrazeTheme
    elif name == "create_gradio_interface":
        from braze_code_gen.ui.gradio_app import create_gradio_interface
        return create_gradio_interface
    elif name == "launch_ui":
        from braze_code_gen.ui.gradio_app import launch_ui
        return launch_ui
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
