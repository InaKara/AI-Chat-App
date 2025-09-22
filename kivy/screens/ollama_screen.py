# --- Purpose -------------------------------------------------------------------
# This module defines the screen where the user enters the **Ollama base URI**
# (e.g., http://127.0.0.1:11434 or http://<PC_LAN_IP>:11434). Typically, the
# visual layout (TextField + button) resides in a KV file, while this class
# exists so the ScreenManager can reference it by name and you can attach any
# Python-side logic later if needed.
#
# We only add comments here—no code lines are changed or removed.

# screens/ollama_screen.py
# MDScreen: KivyMD's Material Design enhanced Screen. A Screen is a full-page
# view that lives inside a ScreenManager; you switch by setting
# `ScreenManager.current = '<screen_name>'`.
from kivymd.uix.screen import MDScreen

# OllamaInputScreen represents the initial page where a user can input or
# confirm the Ollama server URI. The widgets (TextField, button) are typically
# defined in the KV for this screen and accessed via `ids` from the App.
class OllamaInputScreen(MDScreen):
    def __init__(self, **kwargs):
        # super().__init__(**kwargs): initialize the base MDScreen internals
        # (properties, theme integration, event dispatch). Always call this first.
        super().__init__(**kwargs)
        # The ScreenManager uses the `name` attribute to identify screens. This
        # must match the key used when your app navigates to this page, e.g.:
        #   `self.root.current = 'ollama_input_screen'` in your App code.
        self.name = 'ollama_input_screen'