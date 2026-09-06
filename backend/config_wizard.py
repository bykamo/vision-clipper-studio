import getpass
import os
import shutil
import tempfile
from dotenv import dotenv_values, set_key


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
