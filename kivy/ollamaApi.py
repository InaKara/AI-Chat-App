# --- Purpose -------------------------------------------------------------------
# Thin client helpers for talking to an **Ollama** server from Kivy/KivyMD.
#
# WHAT this module does
# - `get_llm_models(url)`: fetch a list of available model names from Ollama.
# - `chat_with_llm(url, model, messages, callback=None)`: send a chat request to
#    Ollama and either return the response or schedule a UI‑safe callback.
#
# WHY it exists
# - Keep network I/O isolated from UI code (screens / widgets).
# - Provide a single place to adapt payloads (prompting, streaming, parameters).
#
# HOW it works
# - Uses `requests` for HTTP calls (blocking). On success, parses JSON payloads.
# - If a `callback` is provided to `chat_with_llm`, schedules it on the Kivy main
#   thread using `Clock.schedule_once`, which is safe for UI updates.

import requests  # requests: simple synchronous HTTP client (GET/POST, JSON helpers).
import json      # json: standard lib for encoding/decoding JSON; here mainly for types/doc.
from kivy.clock import Clock  # Clock: schedules a function on the Kivy main loop.


def get_llm_models(url):
    """
    Return a list of model names available on the Ollama server at `url`.

    First usage notes:
    - f-string: `f"{url}/api/tags"` builds the endpoint URL by inserting `url`.
    - requests.get(url): executes an HTTP GET request and returns a Response object.
    - Response.raise_for_status(): raises for HTTP errors (4xx/5xx) so we can catch them.
    - Response.json(): parses the HTTP response body as JSON into Python objects.

    Ollama `/api/tags` returns `{ "models": [ {"name": "..."}, ... ] }`.
    We filter out names containing "embed" to avoid embedding models in the menu.
    """
    llm_models_url = f"{url}/api/tags"  # endpoint listing local models/tags on Ollama
    got_llm_models = []  # will accumulate plain string names (e.g., "llama3")
    try:
        response = requests.get(llm_models_url)  # perform the HTTP GET
        response.raise_for_status()               # raises an HTTPError on 4xx/5xx
        models_data = response.json()            # parse JSON body into a dict
        for model in models_data.get("models", []):  # dict.get: safe access with default []
            model_name = model['name']
            if model_name.find("embed") == -1: # it is not an embedding model
                got_llm_models.append(model_name)
        return got_llm_models
    except Exception as e:
        # Any network/parse error is caught; we log and return what we have (possibly empty).
        print(f"Error with Ollama: {e}")
        return got_llm_models


def chat_with_llm(url, model, messages, callback=None):
    """
    Send a **chat** request to Ollama and deliver the assistant message.

    Parameters
    - url (str): base URL of the Ollama server, e.g., "http://127.0.0.1:11434".
    - model (str): model name/tag as reported by `/api/tags` or created via `ollama create`.
    - messages (list): OpenAI‑style message list, e.g., [{"role":"user","content":"hi"}, ...].
    - callback (callable|None): if provided, schedule it on the main thread with the
      result dict; otherwise **return** the result dict directly.

    First usage notes:
    - requests.post(url, json=...): sends a JSON body, automatically sets header.
    - Response.json(): parse JSON response body to a Python dict.
    - Clock.schedule_once(func): run `func(dt)` in the next frame on the UI thread.

    Behavior
    - Uses `/api/chat` (native Ollama chat) with `stream=False` for simplicity.
    - Expects a response like `{ "message": {"role": "assistant", "content": "..."}, ... }`.
    - On error, returns a dict with role "error" and a short markdown message.
    """
    chat_url = f"{url}/api/chat"  # native Ollama chat endpoint
    msg_body = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    return_resp = {
        "role": "init",
        "content": "**Initials** in LLM response!"
    }
    try:
        response = requests.post(chat_url, json=msg_body)  # blocking HTTP POST with JSON body
        respDict = response.json()                         # parse JSON into a dict
        if "message" in respDict:
            return_resp = respDict["message"]
        else:
            return_resp = {
                "role": "error",
                "content": "**Error** in LLM response!"
            }
    except Exception as e:
        # On any exception (connection refused, timeout, invalid JSON), log and return error shape.
        print(f"Error with Ollama: {e}")
        return_resp = {
            "role": "error",
            "content": f"**Error** with Ollama: {e}"
        }
    if callback:
        # schedule_once: ensures the callback runs on the Kivy main thread, which is required
        # for UI updates (adding widgets, changing properties, etc.). The lambda wraps the
        # user callback to pass only the response (and discard dt).
        Clock.schedule_once(lambda dt: callback(return_resp))
    else:
        # If no callback was provided, simply return the response to the caller.
        return return_resp

# End