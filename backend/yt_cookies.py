"""Manajemen cookies YouTube (format Netscape) untuk yt-dlp.

Modul ini adalah satu-satunya sumber kebenaran untuk:
- mencari file cookies yang dipakai saat mengunduh,
- memvalidasi isi file sebelum disimpan,
- menyimpan / menghapus file cookies secara atomik,
- menguji apakah cookies masih valid untuk YouTube.

File kanonik selalu ``<project_root>/cookies.txt`` supaya ``yt-dlp`` dan
pengguna melihat lokasi yang sama. Isi file tidak pernah dikembalikan lewat
API — hanya metadata (ukuran, waktu ubah, jumlah domain, dsb).
"""

import os
import tempfile
import threading
from datetime import datetime

COOKIE_FILENAME = "cookies.txt"

# Batas ukuran supaya endpoint tidak bisa dipakai untuk menulis file raksasa.
MAX_COOKIE_BYTES = 5 * 1024 * 1024

# Cookie yang hanya muncul ketika browser benar-benar login ke Google/YouTube.
LOGIN_COOKIE_NAMES = frozenset(
    {
        "SID",
        "HSID",
        "SSID",
        "APISID",
        "SAPISID",
        "LOGIN_INFO",
        "SIDCC",
        "SSIDCC",
        "__Secure-1PSID",
        "__Secure-3PSID",
        "__Secure-1PAPISID",
        "__Secure-3PAPISID",
        "__Secure-1PSIDTS",
        "__Secure-3PSIDTS",
    }
)

# Video pendek yang stabil untuk menguji apakah cookies lolos bot-check.
COOKIE_TEST_URL = "https://www.youtube.com/watch?v=Nnb6DnUjDvE"

# Pesan error yt-dlp yang menandakan cookies tidak (lagi) valid.
INVALID_COOKIE_MARKERS = (
    "sign in to confirm",
    "not a bot",
    "cookies are no longer valid",
    "cookie is no longer valid",
    "failed to decrypt",
    "unable to extract yt initial data",
    "confirm you're not a bot",
    "confirm your age",
)

_lock = threading.Lock()


class CookieFormatError(ValueError):
    """Isi cookies tidak lolos validasi format Netscape."""


def project_root() -> str:
    """Root project (satu level di atas paket ``backend``)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canonical_cookie_path(root: str = None) -> str:
    """Path file cookies yang ditulis oleh Pengaturan Studio."""
    return os.path.join(root or project_root(), COOKIE_FILENAME)


def cookie_candidates(download_dir: str = None, root: str = None) -> list:
    """Urutan lokasi yang dicari saat unduh (paling prioritas di depan).

    Fallback ke ``os.getcwd()`` hanya dipakai pada pemanggilan produksi
    (``root=None``) agar tetap kompatibel dengan file lama; saat ``root``
    diberikan eksplisit (mis. dari tes), pencarian dibatasi ke folder itu.
    """
    candidates = [canonical_cookie_path(root)]
    if download_dir:
        candidates.append(os.path.join(download_dir, COOKIE_FILENAME))
    if root is None:
        candidates.append(os.path.join(os.getcwd(), COOKIE_FILENAME))

    ordered = []
    seen = set()
    for path in candidates:
        real = os.path.abspath(path)
        if real not in seen:
            seen.add(real)
            ordered.append(real)
    return ordered


def _is_usable(path: str) -> bool:
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def resolve_cookie_file(download_dir: str = None, root: str = None) -> str | None:
    """Kembalikan path cookies.txt pertama yang ada dan tidak kosong."""
    for path in cookie_candidates(download_dir, root):
        if _is_usable(path):
            return path
    return None


def _read_text(path: str) -> str:
    size = os.path.getsize(path)
    if size > MAX_COOKIE_BYTES:
        raise CookieFormatError(
            f"File cookies terlalu besar ({size} byte, maksimum {MAX_COOKIE_BYTES} byte)."
        )
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def parse_cookie_text(text: str) -> dict:
    """Validasi isi cookies format Netscape tanpa menyentuh disk.

    Returns:
        dict dengan kunci ``ok``, ``error``, ``cookie_count``, ``domain_count``,
        ``domains``, ``has_login_cookies``, ``ignored_lines``.
    """
    result = {
        "ok": False,
        "error": None,
        "cookie_count": 0,
        "domain_count": 0,
        "domains": [],
        "has_login_cookies": False,
        "ignored_lines": 0,
    }

    if text is None or not str(text).strip():
        result["error"] = "Isi cookies kosong. Tempel isi file cookies.txt atau pilih file."
        return result

    cleaned = str(text).lstrip("\ufeff").strip()
    if len(cleaned.encode("utf-8", errors="ignore")) > MAX_COOKIE_BYTES:
        result["error"] = (
            f"Isi cookies terlalu besar (maksimum {MAX_COOKIE_BYTES // (1024 * 1024)} MB)."
        )
        return result

    domains = []
    seen_domains = set()
    cookie_count = 0
    ignored_lines = 0
    has_login_cookies = False
    youtube_cookie_count = 0

    for raw_line in cleaned.splitlines():
        line = raw_line.strip("\r\n")
        if not line.strip():
            continue

        # yt-dlp menandai cookie HttpOnly dengan prefix "#HttpOnly_"; baris itu
        # tetap baris cookie yang sah.
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_") :]
        elif line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 7:
            ignored_lines += 1
            continue

        domain = parts[0].strip().lower()
        name = parts[5].strip()
        if not domain or not name:
            ignored_lines += 1
            continue

        cookie_count += 1
        bare_domain = domain.lstrip(".")
        if bare_domain not in seen_domains:
            seen_domains.add(bare_domain)
            domains.append(bare_domain)
        if name in LOGIN_COOKIE_NAMES:
            has_login_cookies = True
        if "youtube" in bare_domain or "google" in bare_domain:
            youtube_cookie_count += 1

    if cookie_count == 0:
        result["error"] = (
            "Tidak ada baris cookie yang valid. Pastikan file memakai format Netscape "
            "(kolom dipisahkan TAB), bukan JSON atau format lain."
        )
        return result

    if youtube_cookie_count == 0:
        result["error"] = (
            "File cookies tidak berisi cookie youtube.com / google.com. "
            "Ekspor cookies dari halaman youtube.com, bukan situs lain."
        )
        return result

    result.update(
        {
            "ok": True,
            "cookie_count": cookie_count,
            "domain_count": len(domains),
            "domains": domains[:12],
            "has_login_cookies": has_login_cookies,
            "ignored_lines": ignored_lines,
        }
    )
    return result


def get_cookie_status(root: str = None) -> dict:
    """Metadata file cookies aktif (tanpa membocorkan isi file)."""
    canonical = canonical_cookie_path(root)
    active = resolve_cookie_file(root=root)
    status = {
        "exists": False,
        "path": None,
        "canonical_path": canonical,
        "filename": COOKIE_FILENAME,
        "size_bytes": 0,
        "updated_at": None,
        "cookie_count": 0,
        "domain_count": 0,
        "has_login_cookies": False,
        "valid": False,
        "error": None,
    }

    if not active:
        return status

    status["exists"] = True
    status["path"] = active
    try:
        stat = os.stat(active)
        status["size_bytes"] = stat.st_size
        status["updated_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    except OSError:
        pass

    try:
        parsed = parse_cookie_text(_read_text(active))
    except CookieFormatError as exc:
        status["error"] = str(exc)
        return status
    except OSError as exc:
        status["error"] = f"Gagal membaca file cookies: {exc}"
        return status

    status["valid"] = parsed["ok"]
    status["error"] = parsed["error"]
    status["cookie_count"] = parsed["cookie_count"]
    status["domain_count"] = parsed["domain_count"]
    status["has_login_cookies"] = parsed["has_login_cookies"]
    return status


def save_cookie_text(text: str, root: str = None) -> dict:
    """Validasi lalu tulis cookies ke ``<root>/cookies.txt`` secara atomik.

    Raises:
        CookieFormatError: bila isi bukan format Netscape yang valid.
    """
    parsed = parse_cookie_text(text)
    if not parsed["ok"]:
        raise CookieFormatError(parsed["error"] or "Format cookies tidak valid.")

    cleaned = str(text).lstrip("\ufeff").strip() + "\n"
    target = canonical_cookie_path(root)
    target_dir = os.path.dirname(target) or "."

    with _lock:
        os.makedirs(target_dir, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=target_dir, delete=False, encoding="utf-8", newline="\n"
            ) as handle:
                temp_path = handle.name
                handle.write(cleaned)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, target)
        except Exception:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

    return get_cookie_status(root)


def save_cookie_from_file(source_path: str, root: str = None) -> dict:
    """Salin file cookies dari disk (mis. hasil ekspor ekstensi browser)."""
    if not source_path:
        raise CookieFormatError("Path file cookies kosong.")
    expanded = os.path.expanduser(str(source_path).strip())
    if not os.path.isfile(expanded):
        raise CookieFormatError(f"File tidak ditemukan: {expanded}")

    try:
        text = _read_text(expanded)
    except OSError as exc:
        raise CookieFormatError(f"Gagal membaca file cookies: {exc}") from exc

    return save_cookie_text(text, root=root)


def _is_inside(base: str, path: str) -> bool:
    """True bila ``path`` berada di dalam ``base`` (aman lintas drive di Windows)."""
    try:
        return os.path.commonpath([base, os.path.abspath(path)]) == base
    except ValueError:
        return False


def delete_cookie_file(root: str = None) -> dict:
    """Hapus file cookies (kanonik + kandidat lain di dalam root project)."""
    base = os.path.abspath(root or project_root())
    removed = []
    with _lock:
        for path in cookie_candidates(root=base):
            # Jangan pernah menghapus file di luar project root (mis. cwd user).
            if not _is_inside(base, path):
                continue
            if not os.path.exists(path):
                continue
            try:
                os.remove(path)
                removed.append(path)
            except OSError:
                pass

    status = get_cookie_status(root)
    status["removed"] = removed
    return status


class _SilentLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def _looks_like_cookie_error(message: str) -> bool:
    lowered = (message or "").lower()
    return any(marker in lowered for marker in INVALID_COOKIE_MARKERS)


def _probe_with_ytdlp(cookie_path: str, url: str = COOKIE_TEST_URL) -> dict:
    """Ambil metadata video tanpa mengunduh — bukti cookies lolos bot-check.

    yt-dlp menulis ulang cookie jar saat keluar, jadi probe memakai salinan
    sementara agar file ``cookies.txt`` milik pengguna tidak tersentuh.
    """
    import shutil

    import yt_dlp

    with tempfile.TemporaryDirectory() as temp_dir:
        probe_cookie = os.path.join(temp_dir, COOKIE_FILENAME)
        shutil.copyfile(cookie_path, probe_cookie)

        opts = {
            "cookiefile": probe_cookie,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 20,
            "retries": 1,
            "extractor_args": {"youtube": {"player_client": ["web_embedded", "web"]}},
            "logger": _SilentLogger(),
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            },
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

    if not info:
        raise RuntimeError("yt-dlp tidak mengembalikan metadata video uji.")

    return {
        "title": info.get("title") or "",
        "video_id": info.get("id") or "",
        "uploader": info.get("uploader") or info.get("channel") or "",
    }


def test_cookie_file(root: str = None, probe: bool = True) -> dict:
    """Uji file cookies: validasi format lokal + (opsional) probe ke YouTube."""
    active = resolve_cookie_file(root=root)
    if not active:
        return {
            "ok": False,
            "error": "File cookies.txt belum ada. Tempel cookies lalu klik Simpan Cookies.",
            "message": None,
        }

    try:
        parsed = parse_cookie_text(_read_text(active))
    except (CookieFormatError, OSError) as exc:
        return {"ok": False, "error": str(exc), "message": None}

    if not parsed["ok"]:
        return {"ok": False, "error": parsed["error"], "message": None}

    summary = (
        f"{parsed['cookie_count']} cookie dari {parsed['domain_count']} domain"
        f"{' (login terdeteksi)' if parsed['has_login_cookies'] else ' (tanpa cookie login)'}"
    )

    if not probe:
        return {"ok": True, "message": f"Format valid — {summary}.", "error": None}

    try:
        info = _probe_with_ytdlp(active)
    except Exception as exc:  # noqa: BLE001 - pesan yt-dlp diteruskan apa adanya
        detail = str(exc).strip() or exc.__class__.__name__
        if _looks_like_cookie_error(detail):
            return {
                "ok": False,
                "error": (
                    "Cookies ditolak YouTube (bot-check). Ekspor ulang cookies dari browser "
                    f"yang sudah login, lalu simpan lagi. Detail: {detail[:280]}"
                ),
                "message": None,
            }
        return {"ok": False, "error": f"Gagal menguji cookies: {detail[:280]}", "message": None}

    title = info.get("title") or info.get("video_id") or "video uji"
    return {
        "ok": True,
        "message": f"Cookies valid & lolos bot-check ({summary}). Terbaca: {title[:80]}",
        "error": None,
    }
