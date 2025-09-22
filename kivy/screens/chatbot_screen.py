# --- Purpose -------------------------------------------------------------------
# This module defines the *Chatbot* screen for the app. It contains:
#   • TempSpinWait: a lightweight container used as a temporary spinner/placeholder
#     while the LLM is generating a response (the actual spinner widget is usually
#     defined in the KV for this class).
#   • ChatbotScreen: the main Screen that hosts the chat UI (history list, input
#     field, send button, etc.). The widgets themselves are typically described in
#     KV files and referenced here via ids.
#
# We add comments without changing any code lines. For each imported/used class or
# function, the *first time* it appears, we add a short description of what it does.

# screens/chatbot_screen.py
# MDScreen: KivyMD's Screen implementation; a top-level page that can be managed
# by a ScreenManager. You switch between screens via `ScreenManager.current`.
from kivymd.uix.screen import MDScreen
# MDBoxLayout: a Material Design variant of BoxLayout (lays out children in a row
# or column) with theming and sensible defaults.
from kivymd.uix.boxlayout import MDBoxLayout

# TempSpinWait is a simple container used while waiting for the model's reply.
# Typically the visual spinner is declared in the KV file for this class and this
# Python class is just a hook/type for that template.
class TempSpinWait(MDBoxLayout):
    pass

# ChatbotScreen is the main chat page. It owns the chat history container and the
# input area. In this app, most of the UI structure is in KV; this class sets the
# screen name so the ScreenManager can navigate to it.
class ChatbotScreen(MDScreen):
    def __init__(self, **kwargs):
        # super().__init__(**kwargs): call the parent MDScreen initializer to ensure
        # all base behaviors and properties are set up (ids, theme support, etc.).
        super().__init__(**kwargs)
        # The `name` attribute is how the ScreenManager refers to this screen. It
        # must match the string used when switching screens (e.g., 'chatbot_screen').
        self.name = 'chatbot_screen'
