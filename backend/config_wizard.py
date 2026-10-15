import getpass
import os
import shutil
import tempfile
import threading
from dotenv import dotenv_values, set_key

_config_lock = threading.Lock()

# Provider presets
PROVIDER_PRESETS = {
    "openrouter": {
        "label": "OpenRouter",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "google/gemini-2.0-flash-exp:free",
        "doc_url": "https://openrouter.ai/keys",
    },
    "openai": {
        "label": "OpenAI Resmi",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "doc_url": "https://platform.openai.com/api-keys",
    },
    "groq_llm": {
        "label": "Groq LLM",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.3-70b-versatile",
        "doc_url": "https://console.groq.com/keys",
    },
    "deepseek": {
        "label": "DeepSeek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "doc_url": "https://platform.deepseek.com",
    },
    "custom": {
        "label": "Custom (Ollama / 9Router / vLLM / Lainnya)",
        "endpoint": "",
        "default_model": "",
        "doc_url": "",
    },
}


def _get_env_path(project_root: str = None) -> str:
    if not project_root:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, ".env")


def _reload_env_vars(env_path: str = None):
    """Reload AI-related env vars from .env into os.environ and refresh utils globals."""
    if not env_path:
        env_path = _get_env_path()
    if not os.path.exists(env_path):
        return

    fresh = dotenv_values(env_path)
    for key in ("ROUTER_API_ENDPOINT", "ROUTER_API_KEY", "ROUTER_LLM_MODEL", "GROQ_API_KEY"):
        val = fresh.get(key, "")
        if val is not None:
            os.environ[key] = val

    try:
        import backend.utils as utils_mod
        utils_mod.DEFAULT_ENDPOINT = os.environ.get("ROUTER_API_ENDPOINT", "")
        utils_mod.DEFAULT_API_KEY = os.environ.get("ROUTER_API_KEY", "")
        utils_mod.DEFAULT_LLM_MODEL = os.environ.get("ROUTER_LLM_MODEL", "google/gemini-2.0-flash-exp:free")
        utils_mod.GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    except Exception:
        pass


def get_ai_config(project_root: str = None) -> dict:
    """Read current AI config from .env (with keys masked for security)."""
    env_path = _get_env_path(project_root)
    values = dotenv_values(env_path) if os.path.exists(env_path) else {}

    endpoint = values.get("ROUTER_API_ENDPOINT", "")
    api_key = values.get("ROUTER_API_KEY", "")
    model = values.get("ROUTER_LLM_MODEL", "")
    groq_key = values.get("GROQ_API_KEY", "")

    # Fallback to os.environ if not found in .env
    if not endpoint:
        endpoint = os.environ.get("ROUTER_API_ENDPOINT", "")
    if not api_key:
        api_key = os.environ.get("ROUTER_API_KEY", "")
    if not model:
        model = os.environ.get("ROUTER_LLM_MODEL", "")
    if not groq_key:
        groq_key = os.environ.get("GROQ_API_KEY", "")

    # Detect provider from endpoint
    matched_provider = "custom"
    for pid, preset in PROVIDER_PRESETS.items():
        if preset["endpoint"] and endpoint.rstrip("/") == preset["endpoint"].rstrip("/"):
            matched_provider = pid
            break

    def _is_configured(key: str) -> bool:
        if not key:
            return False
        k = key.strip()
        return bool(k) and not k.startswith("sk-xxxx") and not k.startswith("gsk_xxxx")

    is_llm_ready = _is_configured(api_key) and bool(endpoint) and bool(model)
    is_groq_ready = _is_configured(groq_key)

    return {
        "provider": matched_provider,
        "endpoint": endpoint or "https://openrouter.ai/api/v1/chat/completions",
        "model": model or "google/gemini-2.0-flash-exp:free",
        "api_key_set": _is_configured(api_key),
        "api_key_masked": mask_secret(api_key),
        "groq_key_set": is_groq_ready,
        "groq_key_masked": mask_secret(groq_key),
        "ready": is_llm_ready,
        "groq_ready": is_groq_ready,
        "presets": PROVIDER_PRESETS,
    }


def save_ai_config(
    provider: str = None,
    endpoint: str = None,
    model: str = None,
    api_key: str = None,
    groq_key: str = None,
    project_root: str = None,
) -> dict:
    """Save AI configuration atomically to .env and refresh runtime engine."""
    env_path = _get_env_path(project_root)

    with _config_lock:
        if not os.path.exists(env_path):
            p_root = os.path.dirname(env_path)
            example_path = os.path.join(p_root, ".env.example")
            if os.path.exists(example_path):
                shutil.copy(example_path, env_path)
            else:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("# VisionClipper Studio Environment Config\n")

        # Resolve endpoint and model defaults if provider was selected
        if provider and provider in PROVIDER_PRESETS and provider != "custom":
            preset = PROVIDER_PRESETS[provider]
            if endpoint is None or endpoint == "":
                endpoint = preset["endpoint"]
            if model is None or model == "":
                model = preset["default_model"]

        temp_dir = os.path.dirname(env_path)
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            temp_env_path = tf.name

        try:
            shutil.copyfile(env_path, temp_env_path)
            if endpoint is not None and endpoint.strip() != "":
                set_key(temp_env_path, "ROUTER_API_ENDPOINT", endpoint.strip(), quote_mode="never")
            if model is not None and model.strip() != "":
                set_key(temp_env_path, "ROUTER_LLM_MODEL", model.strip(), quote_mode="never")
            if api_key is not None and api_key.strip() != "":
                set_key(temp_env_path, "ROUTER_API_KEY", api_key.strip(), quote_mode="never")
            if groq_key is not None and groq_key.strip() != "":
                set_key(temp_env_path, "GROQ_API_KEY", groq_key.strip(), quote_mode="never")

            os.replace(temp_env_path, env_path)
        except Exception:
            if os.path.exists(temp_env_path):
                try:
                    os.remove(temp_env_path)
                except OSError:
                    pass
            raise

        _reload_env_vars(env_path)

    return get_ai_config(project_root)


def test_ai_connection(endpoint: str = None, api_key: str = None, model: str = None, project_root: str = None) -> dict:
    """Test LLM connection with a minimal prompt to verify endpoint, model, and api key."""
    import requests

    env_path = _get_env_path(project_root)
    current_values = dotenv_values(env_path) if os.path.exists(env_path) else {}

    if endpoint is not None:
        selected_endpoint = endpoint.strip()
    else:
        selected_endpoint = current_values.get("ROUTER_API_ENDPOINT", "") or os.environ.get("ROUTER_API_ENDPOINT", "")

    if model is not None:
        selected_model = model.strip()
    else:
        selected_model = current_values.get("ROUTER_LLM_MODEL", "") or os.environ.get("ROUTER_LLM_MODEL", "")

    # If api_key not supplied or empty, fall back to saved key
    selected_key = (api_key or "").strip()
    if not selected_key:
        selected_key = current_values.get("ROUTER_API_KEY", "") or os.environ.get("ROUTER_API_KEY", "")

    if not selected_endpoint:
        return {"ok": False, "error": "Endpoint URL belum diisi."}
    if not selected_key or selected_key.startswith("sk-xxxx"):
        return {"ok": False, "error": "LLM API Key belum diisi."}
    if not selected_model:
        return {"ok": False, "error": "Model LLM belum diisi."}

    req_url = selected_endpoint.rstrip("/")
    if not req_url.endswith("/chat/completions"):
        req_url = f"{req_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {selected_key}",
    }
    payload = {
        "model": selected_model,
        "messages": [{"role": "user", "content": "Ping: Balas 'PONG' saja."}],
        "max_tokens": 10,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(req_url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "ok": True,
            "message": f"Koneksi sukses! Model: {selected_model}",
            "reply": reply.strip(),
            "model": selected_model,
        }
    except requests.Timeout:
        return {"ok": False, "error": "Timeout: Server AI tidak merespons dalam 20 detik."}
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        err_msg = ""
        try:
            err_json = e.response.json()
            err_msg = err_json.get("error", {}).get("message", "") or str(err_json)
        except Exception:
            err_msg = e.response.text[:250] if e.response else str(e)
        return {"ok": False, "error": f"HTTP {status_code}: {err_msg}"}
    except Exception as e:
        return {"ok": False, "error": f"Gagal menghubungi server AI: {str(e)[:250]}"}


def test_groq_connection(groq_key: str = None, project_root: str = None) -> dict:
    """Test Groq API key validity using the Groq models endpoint."""
    import requests

    env_path = _get_env_path(project_root)
    current_values = dotenv_values(env_path) if os.path.exists(env_path) else {}

    selected_key = (groq_key or "").strip()
    if not selected_key and groq_key is None:
        selected_key = current_values.get("GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")

    if not selected_key or selected_key.startswith("gsk_xxxx"):
        return {"ok": False, "error": "Groq API Key belum diisi."}

    # If comma-separated, pick first valid key to test
    valid_keys = [k.strip() for k in selected_key.split(",") if k.strip() and not k.strip().startswith("gsk_xxxx")]
    if not valid_keys:
        return {"ok": False, "error": "Groq API Key belum diisi atau format tidak valid."}
    first_key = valid_keys[0]

    headers = {"Authorization": f"Bearer {first_key}"}
    try:
        resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("id") for m in data.get("data", []) if "whisper" in m.get("id", "").lower()]
        return {
            "ok": True,
            "message": "Groq API Key valid!",
            "whisper_models": models or ["whisper-large-v3-turbo", "whisper-large-v3"],
        }
    except requests.Timeout:
        return {"ok": False, "error": "Timeout: Groq server tidak merespons dalam 12 detik."}
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        err_msg = ""
        try:
            err_msg = e.response.json().get("error", {}).get("message", "")
        except Exception:
            err_msg = e.response.text[:200] if e.response else str(e)
        return {"ok": False, "error": f"HTTP {status_code}: {err_msg}"}
    except Exception as e:
        return {"ok": False, "error": f"Gagal menghubungi Groq: {str(e)[:200]}"}


def mask_secret(value: str) -> str:
    """Mask secret API keys for display."""
    if not value or value.startswith("sk-xxxx") or value.startswith("gsk_xxxx"):
        return ""
    if len(value) <= 10:
        return "********"
    return f"{value[:6]}...{value[-4:]}"


def run_interactive_config(project_root: str = None) -> bool:
    """Safely update AI configs in .env without overwriting other variables like YouTube OAuth."""
    if not project_root:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        example_path = os.path.join(project_root, ".env.example")
        if os.path.exists(example_path):
            shutil.copy(example_path, env_path)
        else:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# VisionClipper Studio Environment Config\n")

    current_values = dotenv_values(env_path)
    current_endpoint = current_values.get("ROUTER_API_ENDPOINT") or ""
    current_key = current_values.get("ROUTER_API_KEY") or ""
    current_model = current_values.get("ROUTER_LLM_MODEL") or ""
    current_groq_key = current_values.get("GROQ_API_KEY") or ""

    print("=========================================")
    print("   🤖 KONFIGURASI AI LLM VISION CLIPPER")
    print("=========================================")
    print("Pilih Provider AI yang ingin digunakan:")
    print("  1) OpenRouter (Rekomendasi - Model Beragam, Banyak Opsi Free/Murah)")
    print("  2) OpenAI Resmi (GPT-4o, GPT-4o-mini)")
    print("  3) Custom Endpoint (Groq, 9Router, Ollama, DeepSeek, dll)")
    print()

    choice = input("Pilihan provider [1-3] (Default: 1): ").strip() or "1"
    if choice == "2":
        selected_endpoint = "https://api.openai.com/v1/chat/completions"
        default_model = "gpt-4o-mini"
    elif choice == "3":
        user_endpoint = input(f"Masukkan URL Endpoint (cth: https://api.groq.com/openai/v1/chat/completions) [{current_endpoint}]: ").strip()
        selected_endpoint = user_endpoint or current_endpoint or "https://api.groq.com/openai/v1/chat/completions"
        default_model = current_model or "llama-3.3-70b-versatile"
    else:
        selected_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        default_model = "google/gemini-2.0-flash-exp:free"

    print()
    print(f"Model AI default untuk provider ini: {default_model}")
    user_model = input(f"Gunakan model ini atau ketik model lain (Enter untuk '{default_model}'): ").strip()
    selected_model = user_model or default_model

    print()
    masked_key = mask_secret(current_key)
    if masked_key:
        print(f"LLM API Key saat ini: {masked_key}")
        new_key = getpass.getpass("Masukkan LLM API Key baru (atau Enter untuk tetap gunakan yang lama): ").strip()
        selected_key = new_key if new_key else current_key
    else:
        new_key = getpass.getpass("Masukkan LLM API Key Anda: ").strip()
        selected_key = new_key

    print()
    print("-----------------------------------------")
    print("  🎙️ GROQ CLOUD WHISPER (Transkripsi Super Cepat ~3 detik)")
    print("  Gratis tanpa kartu kredit di: https://console.groq.com")
    print("-----------------------------------------")
    masked_groq = mask_secret(current_groq_key)
    if masked_groq:
        print(f"Groq API Key saat ini: {masked_groq}")
        new_groq = getpass.getpass("Masukkan Groq API Key baru (Enter untuk tetap gunakan yang lama): ").strip()
        selected_groq = new_groq if new_groq else current_groq_key
    else:
        new_groq = getpass.getpass("Masukkan Groq API Key (opsional/bisa diisi nanti): ").strip()
        selected_groq = new_groq

    # Atomic write to temporary file then replace
    temp_dir = os.path.dirname(env_path)
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        temp_env_path = tf.name

    try:
        shutil.copyfile(env_path, temp_env_path)
        set_key(temp_env_path, "ROUTER_API_ENDPOINT", selected_endpoint, quote_mode="never")
        set_key(temp_env_path, "ROUTER_API_KEY", selected_key, quote_mode="never")
        set_key(temp_env_path, "ROUTER_LLM_MODEL", selected_model, quote_mode="never")
        set_key(temp_env_path, "GROQ_API_KEY", selected_groq, quote_mode="never")

        # Atomic replace
        os.replace(temp_env_path, env_path)
        _reload_env_vars(env_path)
    except Exception as e:
        if os.path.exists(temp_env_path):
            try:
                os.remove(temp_env_path)
            except OSError:
                pass
        print(f"[ERROR] Gagal menyimpan konfigurasi: {e}")
        return False

    print()
    print("=========================================")
    print("  ✓ KONFIGURASI AI BERHASIL DISIMPAN!")
    print("=========================================")
    print(f"Endpoint : {selected_endpoint}")
    print(f"Model    : {selected_model}")
    print("API Key  : Terkonfigurasi aman di .env (tanpa menimpa key lain)")
    print("=========================================")
    return True
