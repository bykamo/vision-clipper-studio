import os
import json
import logging
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
LOCAL_TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".visionclipper_youtube_token.json")
TOKEN_FILE = LOCAL_TOKEN_FILE if os.path.exists(LOCAL_TOKEN_FILE) else HOME_TOKEN_FILE
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def _get_active_token_file():
    if os.path.exists(LOCAL_TOKEN_FILE):
        return LOCAL_TOKEN_FILE
    if os.path.exists(HOME_TOKEN_FILE):
        return HOME_TOKEN_FILE
    return LOCAL_TOKEN_FILE

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
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true"
    }
    req = requests.Request("GET", "https://accounts.google.com/o/oauth2/auth", params=params)
    prepared = req.prepare()
    return prepared.url, "state_visionclipper"

def save_credentials_from_code(code: str):
    config = get_client_config()
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code"
    }
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

    # Simpan ke LOCAL_TOKEN_FILE dan HOME_TOKEN_FILE untuk redundansi
    for path in [LOCAL_TOKEN_FILE, HOME_TOKEN_FILE]:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save token to {path}: {e}")
    return True

def get_saved_credentials():
    token_file = None
    for path in [LOCAL_TOKEN_FILE, HOME_TOKEN_FILE]:
        if os.path.exists(path):
            token_file = path
            break

    if not token_file:
        return None

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            for path in [LOCAL_TOKEN_FILE, HOME_TOKEN_FILE]:
                try:
                    with open(path, "w", encoding="utf-8") as f:
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
            return {
                "id": items[0]["id"],
                "title": snippet.get("title", ""),
                "customUrl": snippet.get("customUrl", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
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
    for path in [LOCAL_TOKEN_FILE, HOME_TOKEN_FILE]:
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
