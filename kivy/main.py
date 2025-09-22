# --- High-level overview -------------------------------------------------------
# This is the Kivy/KivyMD app entry point for your local LLM chat client.
# It wires together:
#   - UI screens (Ollama input + Chatbot)
#   - Settings & menus
#   - Calls to your Ollama server via helper functions
# Throughout, we add comments that explain WHAT/WHY/HOW and, at first usage,
# a brief description of each function/class used.

# python core modules
# os: provides portable operating-system utilities (env vars, paths, etc.)
import os
# os.environ: a mapping for environment variables; setting KIVY_GL_BACKEND selects
# the graphics backend before Kivy initializes its windowing system.
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
# sys: interpreter internals; here for frozen-bundle checks and base path logic.
import sys
# re: regular expressions; used for cleaning model output (e.g., removing <THINK> blocks).
import re
# Thread: lightweight parallel execution for non‑blocking HTTP calls to the LLM.
from threading import Thread
# from datetime import datetime  # kept commented by the author for optional timestamping

# kivy & kivymd imports
# Window: access to the app window and IME/soft keyboard behavior.
from kivy.core.window import Window
# Builder: loads .kv language UI files; returns the root widget when load_file is used.
from kivy.lang import Builder
# StringProperty/NumericProperty/ObjectProperty: Kivy observable properties for binding.
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
# dp/sp: device‑independent pixels / scale‑independent pixels for consistent sizing.
from kivy.metrics import dp, sp
# resource_add_path: adds lookup directories for KV includes and other resources.
from kivy.resources import resource_add_path
# Clipboard: system clipboard access (copy/paste).
from kivy.core.clipboard import Clipboard
# platform: utility to detect runtime platform ("android", "win", etc.).
from kivy.utils import platform
# MDApp: KivyMD application base class with Material Design theming/behavior.
from kivymd.app import MDApp
# MDDropdownMenu: Material Design dropdown menu (e.g., the top-right menu here).
from kivymd.uix.menu import MDDropdownMenu
# MDLabel: text label supporting theming and (optionally) markup.
from kivymd.uix.label import MDLabel
# MDFlatButton/MDFloatingActionButton: Material buttons used in dialogs and as inline actions.
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton
# MDDialog: modal dialog container with title/body/buttons.
from kivymd.uix.dialog import MDDialog
# MDSpinner: loading spinner; here referenced via TempSpinWait in chat screen.
from kivymd.uix.spinner import MDSpinner
# MDBoxLayout: box layout with Material defaults.
from kivymd.uix.boxlayout import MDBoxLayout

# other public modules
# m2r2.convert: helper to convert Markdown → reStructuredText for rich display.
from m2r2 import convert

# IMPORTANT: Set this property for keyboard behavior
# Window.softinput_mode controls how the soft keyboard affects layout. "below_target"
# keeps the focused widget visible by pushing content above the keyboard on mobile.
Window.softinput_mode = "below_target"

# Import your screen classes
# These are your custom Kivy Screen implementations defined elsewhere.
from screens.ollama_screen import OllamaInputScreen
from screens.chatbot_screen import ChatbotScreen, TempSpinWait

# import our local api & modules
# get_llm_models: queries the Ollama server for available models.
# chat_with_llm: sends a chat request (with messages) to Ollama and streams/returns a reply.
from ollamaApi import get_llm_models, chat_with_llm
# MyRstDocument: custom widget that renders RST (converted from Markdown) with styling and copy button.
from myrst import MyRstDocument

## Global definitions
__version__ = "0.2.0"
# Determine the base path for your application's resources
# sys.frozen: indicates running from a bundled executable (e.g., PyInstaller);
# sys._MEIPASS: temp dir where bundled resources are unpacked.
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_path = os.path.dirname(os.path.abspath(__file__))
# Build absolute paths for the KV files the app loads and includes.
kv_file_path = os.path.join(base_path, 'main_layout.kv')
kv_files_dir = os.path.join(base_path, 'kv_files')
# Register additional search path so KV includes like `#:include` can be found.
resource_add_path(kv_files_dir)

## The APP definitions
class MyApp(MDApp):
    # Title shown on desktop window chrome; on Android it contributes to app metadata.
    title = "My Ollama Chatbot"
    # StringProperty: bindable URI of the Ollama server (e.g., http://host:11434).
    ollama_uri = StringProperty("")
    # ObjectProperty: holders for dropdown menus created at runtime.
    top_menu = ObjectProperty()
    llm_menu = ObjectProperty()
    # tmp_spin: reference to a transient spinner widget while waiting for responses.
    tmp_spin = ObjectProperty(None)

    def build(self):
        # build(): Kivy/MDApp lifecycle method; must return the root widget of the UI.
        # Typically we set up theme, initialize state, and load the KV tree here.
        # Default Ollama endpoint; user can override via the input screen.
        self.ollama_uri = "http://localhost:11434"
        # selected_llm: name/tag of the active model; set later when models are fetched.
        self.selected_llm = ""
        # messages: running OpenAI‑style chat transcript [{role, content}, ...].
        self.messages = []
        # Theme configuration for KivyMD components.
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Green"
        self.theme_cls.theme_style = "Light"
        # Top menu definition with action mapping used in on_start.
        self.top_menu_items = {
            "Demo": {
                "icon": "youtube",
                "action": "web",
                "url": "https://youtube.com/watch?v=a-azvqDL78k",
            },
            "Documentation": {
                "icon": "file-document-check",
                "action": "web",
                "url": "https://blog.daslearning.in/llm_ai/ollama/kivy-chat.html",
            },
            "Contact Us": {
                "icon": "card-account-phone",
                "action": "web",
                "url": "https://daslearning.in/contact/",
            },
            "Check for update": {
                "icon": "github",
                "action": "update",
                "url": "",
            }
        }
        # Builder.load_file: loads and parses a .kv UI file and returns the root widget.
        return Builder.load_file(kv_file_path)

    def on_start(self):
        # on_start(): lifecycle hook called after the root widget is created and shown.
        # Good place to request permissions, build menus, and initialize state.
        if platform == "android":
            # request_permissions: prompts the user for Android runtime permissions
            # (READ/WRITE external storage here; adjust to your app's needs).
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        # Build the top menu entries for MDDropdownMenu. Each dict defines the row.
        menu_items = [
            {
                "text": menu_key,
                "leading_icon": self.top_menu_items[menu_key]["icon"],
                # on_release: MDDropdownMenu calls this when the user taps an item.
                "on_release": lambda x=menu_key: self.top_menu_callback(x),
                "font_size": sp(36)
            } for menu_key in self.top_menu_items
        ]
        # MDDropdownMenu(...): create the dropdown; open() will display it later.
        self.top_menu = MDDropdownMenu(
            items=menu_items,
            width_mult=4,
        )
        # Flag to prevent overlapping requests while awaiting an LLM response.
        self.is_llm_running = False

    def menu_bar_callback(self, button):
        # Called when the app bar/menu button is pressed; opens the dropdown menu.
        # Assigning the menu's caller anchors it to the button for positioning.
        self.top_menu.caller = button
        self.top_menu.open()

    def txt_dialog_closer(self, instance):
        # Closes the currently open text dialog (MDDialog). `instance` is the button.
        self.txt_dialog.dismiss()

    def top_menu_callback(self, text_item):
        # Handles a menu selection by key (e.g., "Documentation").
        self.top_menu.dismiss()
        action = ""
        url = ""
        try:
            action = self.top_menu_items[text_item]["action"]
            url = self.top_menu_items[text_item]["url"]
        except Exception as e:
            print(f"Erro in menu process: {e}")
        # For web actions, open the link; for update, show a dialog with options.
        if action == "web" and url != "":
            self.open_link(url)
        elif action == "update":
            # MDFlatButton: low‑emphasis button variant used inside MDDialog.
            buttons = [
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="Releases",
                    theme_text_color="Custom",
                    text_color="green",
                    on_release=self.update_checker
                ),
            ]
            self.show_text_dialog(
                "Check for update",
                f"Your version: {__version__}",
                buttons
            )

    def show_toast_msg(self, message, is_error=False):
        # Shows a transient snackbar‑style message at the bottom of the screen.
        # MDSnackbar: container for brief feedback; open() displays it.
        from kivymd.uix.snackbar import MDSnackbar
        bg_color = (0.2, 0.6, 0.2, 1) if not is_error else (0.8, 0.2, 0.2, 1)
        MDSnackbar(
            MDLabel(
                text = message,
                font_style = "Subtitle1" # change size for android
            ),
            md_bg_color=bg_color,
            y=dp(24),
            pos_hint={"center_x": 0.5},
            duration=3
        ).open()

    def show_text_dialog(self, title, text="", buttons=[]):
        # Presents a modal dialog with title/body/buttons. Keep a reference to
        # self.txt_dialog so handlers (e.g., txt_dialog_closer) can dismiss it.
        self.txt_dialog = MDDialog(
            title=title,
            text=text,
            buttons=buttons
        )
        self.txt_dialog.open()

    # ... (rest of your methods like go_to_chatbot, go_back_to_ollama_input, send_message, update_chatbot_welcome)
    def go_to_chatbot(self, instance, ollama_uri_widget):
        # Navigates from the Ollama input screen to the main chatbot screen and
        # stores the configured base URI. `instance` is the button; `ollama_uri_widget`
        # is the TextField whose .text contains the user‑entered URI.
        ollama_uri = ollama_uri_widget.text.strip()
        if ollama_uri:
            self.ollama_uri = ollama_uri
            self.root.current = 'chatbot_screen'
            ollama_uri_widget.text = ""
        else:
            print("Please enter your name.")
            # Provide a friendly default and proceed to the chat screen.
            self.show_toast_msg("Using default Ollama URL")
            self.root.current = 'chatbot_screen'

    def go_back_to_ollama_input(self, instance):
        # Navigate back to the input screen (e.g., to change the Ollama base URI).
        self.root.current = 'ollama_input_screen'

    def add_bot_message(self, instance, msg_to_add):
        # Renders a bot/assistant message in the chat history.
        # convert(): Markdown → reStructuredText for richer formatting with your custom widget.
        rst_txt = convert(msg_to_add)
        # MyRstDocument: custom RST display widget with configurable base font and padding.
        bot_msg_label = MyRstDocument(
            text = rst_txt,
            base_font_size=36,
            padding=[dp(10), dp(10)],
            background_color = self.theme_cls.bg_normal
        )
        # MDFloatingActionButton: small floating button; here used as an inline copy icon.
        copy_btn = MDFloatingActionButton(
            icon="content-copy",
            type="small",
            theme_icon_color="Custom",
            md_bg_color='#e9dff7',
            icon_color='#211c29',
        )
        # bind(): connects an event (on_release) to a Python callback.
        copy_btn.bind(on_release=self.copy_rst)
        bot_msg_label.add_widget(copy_btn)
        # add_widget(): adds the new message widget to the scrolling chat container.
        self.chat_history_id.add_widget(bot_msg_label)

    def copy_rst(self, instance):
        # Copies the (rendered) RST text from the MyRstDocument widget to the clipboard.
        # instance.parent is the MyRstDocument; its .text holds the RST content.
        rst_txt = instance.parent.text
        Clipboard.copy(rst_txt)

    def add_usr_message(self, msg_to_add):
        # Appends a right‑aligned user message to the chat history using MDLabel with markup.
        usr_msg_label = MDLabel(
            size_hint_y=None,
            markup=True,
            halign='right',
            valign='top',
            padding=[dp(10), dp(10)],
            font_style="Subtitle1",
            allow_selection = True,
            allow_copy = True,
            text = f"{msg_to_add}",
        )
        # bind(texture_size=...): updates widget size when its texture (rendered text) changes.
        usr_msg_label.bind(texture_size=usr_msg_label.setter('size'))
        self.chat_history_id.add_widget(usr_msg_label)

    def send_message(self, button_instance, chat_input_widget):
        # Sends the user's message to the LLM if not already awaiting a response.
        if self.is_llm_running:
            self.show_toast_msg("Please wait for the current response", is_error=True)
            return
        user_message = chat_input_widget.text.strip()
        if user_message:
            # Compose display text and OpenAI‑style content for the message history.
            user_message_add = f"[b][color=#2196F3]You:[/color][/b] {user_message}"
            self.messages.append(
                {
                    "role": "user",
                    "content": user_message
                }
            )
            self.add_usr_message(user_message_add)
            chat_input_widget.text = "" # blank the input
            # TempSpinWait: small spinner widget to indicate a pending response.
            self.tmp_spin = TempSpinWait()
            self.chat_history_id.add_widget(self.tmp_spin)
            # Thread(target=..., args=..., daemon=True): run blocking I/O off the UI thread
            # so the app stays responsive. chat_with_llm will call back into ollama_callback.
            ollama_thread = Thread(target=chat_with_llm, args=(self.ollama_uri, self.selected_llm, self.messages[-3:], self.ollama_callback), daemon=True)
            ollama_thread.start()
            self.is_llm_running = True
        else:
            self.show_toast_msg("Please type a message!", is_error=True)

    def ollama_callback(self, llm_resp):
        # Receives streamed/final responses from chat_with_llm and updates UI/state.
        if llm_resp["role"] == "assistant":
            self.messages.append(llm_resp)
        api_msg = llm_resp["content"]
        # re.sub: regex replace; here removes any <THINK>...</THINK> meta sections from the model output.
        api_msg = re.sub(r'<THINK>.*?</THINK>', '', api_msg, flags=re.DOTALL | re.IGNORECASE)
        api_msg = f"**Bot:** \n{api_msg}"
        # Remove spinner, mark not running, and render the bot message.
        self.chat_history_id.remove_widget(self.tmp_spin)
        self.is_llm_running = False
        self.add_bot_message(self, api_msg)

    def label_copy(self, label_text):
        # Strips Kivy markup tags from a string and copies plain text to clipboard.
        plain_text = re.sub(r'\[/?(?:color|b|i|u|s|sub|sup|font|font_context|font_family|font_features|size|ref|anchor|text_language).*?\]', '', label_text)
        Clipboard.copy(plain_text)

    def llm_menu_callback(self, text_item, screen):
        # Updates currently selected model and reflects it in the menu button text.
        self.llm_menu.dismiss()
        self.selected_llm = text_item
        screen.ids.llm_menu.text = self.selected_llm

    def update_chatbot_welcome(self, screen_instance):
        # Called when the chat screen is shown; wires IDs, fetches models, builds the LLM menu,
        # and displays an initial info label with the currently configured Ollama URI.
        screen_instance.ids.chat_history_id.background_color = self.theme_cls.bg_normal
        self.chat_history_id = screen_instance.ids.chat_history_id
        if self.ollama_uri:
            # get_llm_models(base_url): queries Ollama for available models; returns a list of names.
            ollama_models = get_llm_models(self.ollama_uri)
            # Build dropdown menu items for each model.
            menu_items = [
                {
                    "text": f"{model_name}",
                    "leading_icon": "robot-happy",
                    "on_release": lambda x=f"{model_name}": self.llm_menu_callback(x, screen_instance),
                    "font_size": sp(24)
                } for model_name in ollama_models
            ]
            # Create the dropdown menu (items assigned below so we can set defaults first).
            self.llm_menu = MDDropdownMenu(
                md_bg_color="#bdc6b0",
                caller=screen_instance.ids.llm_menu,
                items=[],
            )
            if len(ollama_models) >= 1:
                self.selected_llm = menu_items[0]["text"]
                screen_instance.ids.llm_menu.text = self.selected_llm
                self.llm_menu.items = menu_items
            else:
                # No models found: leave menu empty and reflect "None" in the button text.
                print("No Ollama LLM found!")
                self.llm_menu.items = []
                self.selected_llm = "None"
                screen_instance.ids.llm_menu.text = self.selected_llm
            # current_timestamp = datetime.now()
            # current_time = current_timestamp.strftime('%H%M%S')
            # MDLabel here shows a one‑time informational line in the chat history.
            init_msg_label = MDLabel(
                size_hint_y=None,
                markup=True,
                halign='center',
                valign='top',
                padding=[dp(10), dp(10)],
                font_style="Subtitle1",
                text = f"[color=#0000FF]Init:[/color] Your Ollama URI: {self.ollama_uri}",
                # id = f"label-{current_time}"
            )
            init_msg_label.bind(texture_size=init_msg_label.setter('size'))
            screen_instance.ids.chat_history_id.add_widget(init_msg_label)
            # screen_instance.ids.chat_history_id.text = f"Your Ollama URI: {self.ollama_uri}"
        else:
            print("Ollama URI not found")
            # add some popup error

    def update_checker(self, instance):
        # Closes the version dialog and opens the Releases page for manual updates.
        self.txt_dialog.dismiss()
        self.open_link("https://github.com/daslearning-org/Ollama-AI-Chat-App/releases")

    def open_link(self, url):
        # webbrowser.open(url): launches the default browser to the given URL.
        import webbrowser
        webbrowser.open(url)

# Standard Python entry point: only run the app when this file is executed directly.
if __name__ == '__main__':
    MyApp().run()