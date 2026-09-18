import os
import json
import logging
import secrets
import time
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from backend.utils import log

# Allow HTTP for local testing OAuth callback
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

logger = logging.getLogger("youtube_uploader")

HOME_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".visionclipper_youtube_token.json")
TOKEN_FILE = HOME_TOKEN_FILE
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

# Pending OAuth states: state -> {"created_at": timestamp, "code_verifier": optional}
_PENDING_OAUTH_STATES = {}
OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes

def _cleanup_expired_states():
    now = time.time()
    expired = [s for s, data in _PENDING_OAUTH_STATES.items() if now - data.get("created_at", 0) > OAUTH_STATE_TTL_SECONDS]
    for s in expired:
        _PENDING_OAUTH_STATES.pop(s, None)

def generate_oauth_state() -> str:
    """Generate cryptographically secure state token with expiration tracking."""
    _cleanup_expired_states()
    state = secrets.token_urlsafe(32)
    _PENDING_OAUTH_STATES[state] = {"created_at": time.time()}
    return state

def _consume_oauth_state(state: str):
    """Return the valid pending OAuth state once, then remove it."""
    if not state:
        return None
    _cleanup_expired_states()
    state_info = _PENDING_OAUTH_STATES.pop(state, None)
    if not state_info:
        return None
    if (time.time() - state_info.get("created_at", 0)) > OAUTH_STATE_TTL_SECONDS:
        return None
    return state_info

def verify_and_consume_oauth_state(state: str) -> bool:
    """Validate that state is present, matching, and not expired, then remove it (single use)."""
    return _consume_oauth_state(state) is not None

def _get_active_token_file():
    return HOME_TOKEN_FILE

def _load_env_if_needed():
    """Ensure .env is loaded if values are not present in os.environ."""
    if not os.environ.get("YOUTUBE_CLIENT_ID"):
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

def get_client_config():
    _load_env_if_needed()
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    redirect_uri = os.environ.get("YOUTUBE_REDIRECT_URI", "http://localhost:5050/api/social/youtube/callback")

    if not client_id or not client_secret:
        raise ValueError("YOUTUBE_CLIENT_ID atau YOUTUBE_CLIENT_SECRET belum dikonfigurasi di file .env")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }

def get_auth_url():
    config = get_client_config()
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    state = generate_oauth_state()
    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=config["redirect_uri"]
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
            state=state
        )
        # Store code_verifier for PKCE exchange if generated
        if hasattr(flow, "code_verifier") and flow.code_verifier:
            _PENDING_OAUTH_STATES[state]["code_verifier"] = flow.code_verifier
        return auth_url, state
    except Exception as e:
        logger.warning(f"Google Flow authorization_url fallback: {e}")
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state
        }
        req = requests.Request("GET", "https://accounts.google.com/o/oauth2/auth", params=params)
        prepared = req.prepare()
        return prepared.url, state

def save_credentials_from_code(code: str, state: str = None):
    state_info = {}
    if state is not None:
        state_info = _consume_oauth_state(state)
        if not state_info:
            raise ValueError("State OAuth tidak valid atau telah kedaluwarsa.")
    config = get_client_config()
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    token_data = None
    # Coba gunakan Google Flow dengan state / code_verifier jika ada
    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=config["redirect_uri"]
        )
        flow.code_verifier = state_info.get("code_verifier")
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
    except Exception as e:
        logger.warning(f"Flow.fetch_token fallback ke HTTP requests: {e}")
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code"
        }
        if state_info.get("code_verifier"):
            data["code_verifier"] = state_info["code_verifier"]
        res = requests.post(token_url, data=data)
        token_json = res.json()
        if "error" in token_json:
            raise RuntimeError(f"Token exchange failed: {token_json.get('error_description', token_json.get('error'))}")

        token_data = {
            "token": token_json.get("access_token"),
            "refresh_token": token_json.get("refresh_token"),
            "token_uri": token_url,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scopes": SCOPES
        }

    # Jika refresh_token tidak dikembalikan (karena sudah pernah di-consent), pertahankan yang lama
    active_token_file = _get_active_token_file()
    if not token_data["refresh_token"] and os.path.exists(active_token_file):
        try:
            with open(active_token_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                token_data["refresh_token"] = old_data.get("refresh_token")
        except Exception:
            pass

    # Simpan token secara eksklusif ke HOME_TOKEN_FILE dengan permission 0600
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(HOME_TOKEN_FILE, flags, mode)
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)
    except Exception as e:
        logger.debug(f"Could not save token to {HOME_TOKEN_FILE}: {e}")
    return True

def get_saved_credentials():
    token_file = HOME_TOKEN_FILE if os.path.exists(HOME_TOKEN_FILE) else None
    if not token_file:
        return None

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            if creds.expiry:
                token_data["expiry"] = creds.expiry.strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                mode = 0o600
                fd = os.open(HOME_TOKEN_FILE, flags, mode)
                with open(fd, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, indent=2)
            except Exception:
                pass
        return creds
    except Exception as e:
        logger.warning(f"Error loading YouTube token: {e}")
        return None

def get_channel_info():
    creds = get_saved_credentials()
    if not creds:
        return None
    try:
        youtube = build("youtube", "v3", credentials=creds)
        res = youtube.channels().list(mine=True, part="snippet,statistics").execute()
        items = res.get("items", [])
        if items:
            snippet = items[0]["snippet"]
            stats = items[0].get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = next(
                (thumbnails.get(size, {}).get("url") for size in ("high", "medium", "default") if thumbnails.get(size, {}).get("url")),
                ""
            )
            return {
                "id": items[0]["id"],
                "title": snippet.get("title", ""),
                "customUrl": snippet.get("customUrl", ""),
                "thumbnail": thumbnail,
                "subscriberCount": stats.get("subscriberCount", "0"),
                "videoCount": stats.get("videoCount", "0")
            }
        else:
            return None
    except Exception as e:
        logger.warning(f"Error fetching channel info: {e}")
        return None

def disconnect_youtube():
    removed = False
    for path in [HOME_TOKEN_FILE, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".visionclipper_youtube_token.json")]:
        if os.path.exists(path):
            try:
                os.remove(path)
                removed = True
            except Exception as e:
                logger.debug(f"Error removing {path}: {e}")
    return True

def upload_video_to_youtube(video_path: str, title: str, description: str = "", tags: list = None, privacy_status: str = "private"):
    creds = get_saved_credentials()
    if not creds:
        raise ValueError("Akun YouTube belum terhubung. Silakan login terlebih dahulu.")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")

    # Normalisasi privacy status ('public', 'unlisted', 'private')
    valid_privacies = {"public", "unlisted", "private"}
    privacy_status = (privacy_status or "private").lower().strip()
    if privacy_status not in valid_privacies:
        privacy_status = "private"

    youtube = build("youtube", "v3", credentials=creds)

    clean_tags = []
    if tags:
        for t in tags:
            clean_t = t.replace("#", "").strip()
            if clean_t and clean_t not in clean_tags:
                clean_tags.append(clean_t)
    if "Shorts" not in clean_tags:
        clean_tags.append("Shorts")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description or f"{title}\n\n#Shorts",
            "tags": clean_tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=1024*1024*5, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response.get("id")
    return {
        "video_id": video_id,
        "title": title,
        "url": f"https://youtu.be/{video_id}",
        "shorts_url": f"https://www.youtube.com/shorts/{video_id}",
        "privacy": privacy_status
    }
