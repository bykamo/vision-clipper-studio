"""
Emoji overlay engine — renders TRUE-COLOR emoji for burned-in subtitles.

Why this exists
---------------
libass (as bundled in imageio-ffmpeg's ffmpeg 7.1) can only draw *outline*
glyphs: ``ass_font_get_glyph`` always passes ``FT_LOAD_NO_BITMAP`` and
``FT_LOAD_COLOR`` is never used. Both CBDT (``NotoColorEmoji.ttf``) and COLR
fonts therefore come out monochrome or as tofu — this is architectural, not a
version issue. So the subtitle pipeline cannot produce phone-like color emoji
on its own.

What we do instead
------------------
1. The ASS file keeps the emoji character so libass still *reserves* the exact
   horizontal space for it, but the glyph is drawn fully transparent
   (``\\alpha&HFF&``). Text layout is therefore byte-identical to a normal
   subtitle — no re-centering, no shifted words.
2. We reproduce libass' own layout maths (advance widths from the resolved font
   tables, bottom-anchored baseline from ``usWinDescent``) to learn where that
   transparent slot sits on screen.
3. Pillow rasterises the real color emoji (``NotoColorEmoji.ttf`` with
   ``embedded_color=True``) into an RGBA PNG that fills the slot.
4. ffmpeg overlays those PNGs on top of the finished video with
   ``enable='between(t,start,end)'``.

The result is a subtitle that looks exactly like before, except emojis are now
full colour — same artwork as on a phone, no tint, no tofu.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time

from backend.utils import log, TEMP_DIR

try:  # Pillow is required for the actual colour rasterisation
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except Exception:  # pragma: no cover - optional dependency
    Image = ImageDraw = ImageFont = None
    _PIL_OK = False

try:  # fontTools gives us the same metrics libass uses
    from fontTools.ttLib import TTFont, TTCollection
    _FT_OK = True
except Exception:  # pragma: no cover - optional dependency
    TTFont = TTCollection = None
    _FT_OK = False


COLOR_EMOJI_FILE = "NotoColorEmoji.ttf"
MONO_EMOJI_FILE = "NotoEmoji.ttf"
MONO_EMOJI_FAMILY = "Noto Emoji"

# Pillow can only load the font at its native bitmap strike size.
_COLOR_STRIKE = 109
# Emoji artwork is drawn slightly larger than the text em box: Noto Color Emoji
# glyphs have generous padding, so 1.0 would look small next to the words.
EMOJI_SIZE_SCALE = 1.18
# Fonts libass resolves that belong to the emoji slot (never measured as text).
_EMOJI_FAMILIES = {"noto emoji", "noto color emoji"}


# ──────────────────────────────────────────────────────────────────────────────
# Emoji character detection (kept in sync with renderer._EMOJI_PATTERN)
# ──────────────────────────────────────────────────────────────────────────────
EMOJI_CHAR_RANGES = (
    r"\U0001F000-\U0001FAFF"
    r"\u2190-\u21FF"
    r"\u2300-\u23FF"
    r"\u2460-\u24FF"
    r"\u25A0-\u25FF"
    r"\u2600-\u27BF"
    r"\u2B00-\u2BFF"
    r"\u3030\u303D\u3297\u3299"
    r"\u2122\u2139\u2049\u203C"
)
_EMOJI_CHAR = f"[{EMOJI_CHAR_RANGES}]"
EMOJI_CLUSTER = (
    r"[\U0001F1E6-\U0001F1FF]{2}"
    rf"|{_EMOJI_CHAR}[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?"
    rf"(?:\u200D{_EMOJI_CHAR}[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?)*"
    r"|\u20E3"
)
EMOJI_RE = re.compile(f"({EMOJI_CLUSTER})")

_ASS_TAG_RE = re.compile(r"\{([^}]*)\}")
_ASS_TOKEN_RE = re.compile(r"\\[a-zA-Z]+[^\\{}]*")


def strip_variation_selectors(text: str) -> str:
    return text.replace("\ufe0e", "").replace("\ufe0f", "")


# ──────────────────────────────────────────────────────────────────────────────
# Font file discovery
# ──────────────────────────────────────────────────────────────────────────────
def _system_font_dirs():
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return [
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            "/Library/Fonts",
            os.path.join(home, "Library", "Fonts"),
        ]
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        return [
            os.path.join(windir, "Fonts"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
        ]
    return [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.join(home, ".fonts"),
        os.path.join(home, ".local", "share", "fonts"),
    ]


_FONT_INDEX = None
_FONT_INDEX_KEY = None


def _iter_faces(path):
    """Yield ``(index, postscript_name, family, subfamily, weight)`` for a font file."""
    try:
        if path.lower().endswith((".ttc", ".otc")):
            fonts = list(TTCollection(path, lazy=True).fonts)
        else:
            fonts = [TTFont(path, lazy=True)]
    except Exception:
        return
    for i, font in enumerate(fonts):
        try:
            ps = font["name"].getDebugName(6) or ""
            family = font["name"].getDebugName(1) or ""
            sub = font["name"].getDebugName(2) or ""
            weight = int(getattr(font["OS/2"], "usWeightClass", 400) or 400)
        except Exception:
            continue
        if ps or family:
            yield i, ps.strip(), family.strip(), sub.strip(), weight


def _build_font_index(fonts_dir):
    """Map lowercased PostScript name AND ``family subfamily`` -> (path, index)."""
    dirs = []
    if fonts_dir and os.path.isdir(fonts_dir):
        dirs.append(fonts_dir)
    dirs.extend(d for d in _system_font_dirs() if os.path.isdir(d))

    index = {}
    for directory in dirs:
        for root, _subdirs, files in os.walk(directory):
            for name in files:
                if not name.lower().endswith((".ttf", ".otf", ".ttc", ".otc")):
                    continue
                path = os.path.join(root, name)
                for idx, ps, family, sub, weight in _iter_faces(path):
                    record = {"path": path, "index": idx, "family": family,
                              "subfamily": sub, "weight": weight}
                    for key in {ps.lower(), f"{family} {sub}".strip().lower()}:
                        if key and key not in index:
                            index[key] = record
    return index


def get_font_index(fonts_dir):
    """Cached font-name index (persisted to disk so we only walk fonts once)."""
    global _FONT_INDEX, _FONT_INDEX_KEY
    if not _FT_OK:
        return {}

    dirs = []
    if fonts_dir and os.path.isdir(fonts_dir):
        dirs.append(fonts_dir)
    dirs.extend(d for d in _system_font_dirs() if os.path.isdir(d))
    key = "|".join(f"{d}:{os.path.getmtime(d) if os.path.isdir(d) else 0}" for d in dirs)

    if _FONT_INDEX is not None and _FONT_INDEX_KEY == key:
        return _FONT_INDEX

    cache_path = os.path.join(TEMP_DIR, ".font_index.json")
    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("key") == key and isinstance(cached.get("index"), dict):
            _FONT_INDEX, _FONT_INDEX_KEY = cached["index"], key
            return _FONT_INDEX
    except Exception:
        pass

    index = _build_font_index(fonts_dir)
    _FONT_INDEX, _FONT_INDEX_KEY = index, key
    try:
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump({"key": key, "index": index}, fh)
    except Exception:
        pass
    return index


def resolve_libass_font(family, bold, fonts_dir, ffmpeg_bin=None, job_id=None):
    """Ask libass which font file it really picks for ``family``/``bold``.

    ``Plus Jakarta Sans`` / ``Montserrat`` are usually *not* installed, so libass
    silently falls back to something else (Helvetica on macOS). Measuring text
    with the requested family would then be wrong, so we let libass tell us the
    truth through its ``fontselect`` trace.
    """
    if not _FT_OK:
        return None

    resolved = _probe_fontselect(family, bold, fonts_dir, ffmpeg_bin)
    index = get_font_index(fonts_dir)
    if resolved:
        path, index_no, ps_name = resolved
        if path and os.path.exists(path):
            return {"path": path, "index": max(0, index_no)}
        hit = index.get((ps_name or "").strip().lower())
        if hit:
            return {"path": hit["path"], "index": hit["index"]}

    # Fallback: trust the requested family name.
    for key in (family.lower(), f"{family} Bold".lower(), f"{family} Regular".lower()):
        hit = index.get(key)
        if hit:
            return {"path": hit["path"], "index": hit["index"]}
    return None


_PROBES = {}


def _probe_fontselect(family, bold, fonts_dir, ffmpeg_bin):
    cache_key = (family, bool(bold), fonts_dir)
    if cache_key in _PROBES:
        return _PROBES[cache_key]

    if ffmpeg_bin is None:
        try:
            from backend.utils import get_ffmpeg_binary
            ffmpeg_bin = get_ffmpeg_binary()
        except Exception:
            _PROBES[cache_key] = None
            return None

    ass = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 320\nPlayResY: 180\n"
        "WrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: P,{family},48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        f"{'-1' if bold else '0'},0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:01.00,P,,0,0,0,,HH\n"
    )
    probe_path = os.path.join(TEMP_DIR, f".fontselect_{int(time.time() * 1000)}.ass")
    try:
        with open(probe_path, "w", encoding="utf-8") as fh:
            fh.write(ass)
        fonts_opt = ""
        if fonts_dir and os.path.isdir(fonts_dir):
            escaped = fonts_dir.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
            fonts_opt = f":fontsdir='{escaped}'"
        escaped_ass = probe_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        result = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-loglevel", "verbose", "-y",
             "-f", "lavfi", "-i", "color=c=black:s=320x180:d=1",
             "-vf", f"subtitles='{escaped_ass}'{fonts_opt}",
             "-frames:v", "1", "-f", "null", "-"],
            capture_output=True, timeout=30,
        )
        stderr = result.stderr.decode("utf-8", "replace")
        parsed = None
        for line in stderr.splitlines():
            match = re.search(r"fontselect: \(([^)]*)\) -> ([^,]+), (-?\d+), (\S+)", line)
            if not match:
                continue
            requested = [part.strip() for part in match.group(1).split(",")]
            if requested and requested[0].lower() == family.lower():
                parsed = (match.group(2).strip(), int(match.group(3)), match.group(4).strip())
                break
        _PROBES[cache_key] = parsed
        return parsed
    except Exception:
        _PROBES[cache_key] = None
        return None
    finally:
        try:
            if os.path.exists(probe_path):
                os.remove(probe_path)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Font metrics (mirrors libass' own scaling)
# ──────────────────────────────────────────────────────────────────────────────
class FontMetrics:
    """Advance widths + vertical metrics exactly as libass computes them.

    libass scales a style's ``Fontsize`` so that ``usWinAscent + usWinDescent``
    maps onto ``Fontsize`` pixels — i.e. ``em_px = Fontsize * upem / (winAsc+winDesc)``.
    Verified empirically against rendered frames (error < 4px over many strings).
    """

    def __init__(self, path, index=0):
        self.tt = TTFont(path, fontNumber=max(0, index))
        self.upem = self.tt["head"].unitsPerEm or 1000
        os2 = self.tt["OS/2"]
        self.win_asc = getattr(os2, "usWinAscent", self.upem) or self.upem
        self.win_desc = getattr(os2, "usWinDescent", 0) or 0
        self.cmap = self.tt.getBestCmap() or {}
        self.hmtx = self.tt["hmtx"]

    @property
    def _denom(self):
        return (self.win_asc + self.win_desc) or self.upem

    def em_px(self, font_size):
        return float(font_size) * self.upem / self._denom

    def baseline_from_bottom(self, font_size, bottom_y):
        """Baseline Y for a bottom-anchored line whose box bottom is ``bottom_y``."""
        return bottom_y - self.win_desc * self.em_px(font_size) / self.upem

    def advance(self, text, font_size):
        em = self.em_px(font_size)
        total = 0.0
        for char in text:
            glyph = self.cmap.get(ord(char), ".notdef")
            try:
                width = self.hmtx[glyph][0]
            except KeyError:
                width = self.hmtx[".notdef"][0]
            total += width * em / self.upem
        return total

# ──────────────────────────────────────────────────────────────────────────────
# ASS dialogue parsing
# ──────────────────────────────────────────────────────────────────────────────
def parse_ass_file(ass_path):
    """Extract subtitle styles and dialogue events from a generated .ass file.

    Returns ``(styles, dialogues)`` where ``styles`` maps a style name to
    ``{"font": str, "size": float, "margin_v": int, "alignment": int}`` and
    ``dialogues`` is a list of ``{"style", "start", "end", "text"}``.
    """
    styles, dialogues = {}, []
    try:
        with open(ass_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except Exception:
        return styles, dialogues

    section = None
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        if section in ("v4+ styles", "v4 styles"):
            if not line.lower().startswith("style:"):
                continue
            body = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in body.split(",")]
            # Name, Fontname, Fontsize, Primary, Secondary, Outline, Back,
            # Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing,
            # Angle, BorderStyle, Outline, Shadow, Alignment, MarginL,
            # MarginR, MarginV, Encoding
            if len(parts) < 22:
                continue
            try:
                styles[parts[0]] = {
                    "font": parts[1],
                    "size": float(parts[2]),
                    "bold": int(float(parts[7] or 0)) != 0,
                    "alignment": int(float(parts[18] or 2)),
                    "margin_v": int(float(parts[21] or 0)),
                }
            except (ValueError, IndexError):
                continue
        elif section == "events":
            if not line.lower().startswith("dialogue:"):
                continue
            body = line.split(":", 1)[1].lstrip()
            parts = body.split(",", 9)
            if len(parts) < 10:
                continue
            try:
                start = _ass_time(parts[1])
                end = _ass_time(parts[2])
            except ValueError:
                continue
            dialogues.append({
                "style": parts[3].strip(),
                "start": start,
                "end": end,
                "text": parts[9],
            })
    return styles, dialogues


def _ass_time(value):
    value = value.strip()
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError(value)
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def split_runs(text, default_font, default_size):
    """Split an ASS dialogue payload into typed runs.

    Returns a list of dicts with ``text``, ``font``, ``size``, ``visible`` and
    ``is_emoji``. ``\\fn`` and ``\\fs`` overrides are tracked so per-word size
    pops (the active word in the TikTok style) are measured correctly, and
    ``\\alpha``/``\\1a`` are tracked so emoji on hidden (future) words are not
    painted yet.
    """
    runs = []
    font, size, hidden = default_font, default_size, False
    # ``pending_emoji_slot`` marks the next run as the emoji placeholder and
    # remembers whether the *word* it belongs to is visible. It is captured when
    # the \fn switch happens, i.e. before the placeholder's own \alpha&HFF& tag,
    # so the placeholder being transparent never makes its word look hidden.
    pending_emoji_slot = False
    pending_emoji_visible = True
    pos = 0

    def flush(end):
        nonlocal pos, pending_emoji_slot, pending_emoji_visible
        if end > pos:
            runs.append({
                "text": text[pos:end],
                "font": font,
                "size": size,
                "visible": pending_emoji_visible if pending_emoji_slot else not hidden,
                "is_emoji": pending_emoji_slot,
            })
            pending_emoji_slot = False
            pending_emoji_visible = True
        pos = end

    for match in _ASS_TAG_RE.finditer(text):
        flush(match.start())
        for token in _ASS_TOKEN_RE.findall(match.group(1)):
            lowered = token.lower()
            if lowered.startswith("\\fn"):
                name = token[3:].strip()
                font = default_font if not name else name
                if font.strip().lower() in _EMOJI_FAMILIES:
                    pending_emoji_slot = True
                    pending_emoji_visible = not hidden
            elif lowered.startswith("\\fs") and not lowered.startswith(("\\fsc", "\\fsp", "\\fsty")):
                try:
                    size = float(token[3:])
                except ValueError:
                    pass
            elif lowered.startswith("\\alpha"):
                hidden = _alpha_is_hidden(token[6:])
            elif lowered.startswith("\\1a"):
                hidden = _alpha_is_hidden(token[3:])
        pos = match.end()
    flush(len(text))
    return runs


def _alpha_is_hidden(value):
    """Parse an ASS alpha value (``&HFF&``, ``FF``, ``&H00&``, ``255``).

    ASS writes alpha as hexadecimal in ``&HAABBGGRR`` style, so the ``H`` prefix
    and the trailing ``&`` must both be stripped before parsing.
    """
    text = (value or "").strip().upper()
    if text.startswith("&H"):
        text = text[2:]
    text = text.strip("&").strip()
    if not text:
        return False
    try:
        return int(text, 16) >= 0xF0
    except ValueError:
        try:
            return int(text, 10) >= 240
        except ValueError:
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Colour emoji rasterisation
# ──────────────────────────────────────────────────────────────────────────────
def _emoji_cache_dir():
    path = os.path.join(TEMP_DIR, "emoji_png")
    os.makedirs(path, exist_ok=True)
    return path


def render_color_emoji(emoji, target_px, fonts_dir):
    """Rasterise one emoji to an RGBA PIL image at ``target_px`` height."""
    if not _PIL_OK:
        return None
    font_path = os.path.join(fonts_dir, COLOR_EMOJI_FILE)
    if not os.path.exists(font_path):
        return None

    target_px = max(8, int(round(target_px)))
    key = hashlib.sha1(
        f"{emoji}|{target_px}|{os.path.getmtime(font_path)}".encode("utf-8")
    ).hexdigest()[:16]
    cache_path = os.path.join(_emoji_cache_dir(), f"{key}.png")
    if os.path.exists(cache_path):
        try:
            return Image.open(cache_path).convert("RGBA")
        except Exception:
            pass

    try:
        font = ImageFont.truetype(font_path, _COLOR_STRIKE)
    except Exception:
        return None

    canvas = Image.new("RGBA", (_COLOR_STRIKE * 3, _COLOR_STRIKE * 3), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((_COLOR_STRIKE, _COLOR_STRIKE), emoji,
                                font=font, embedded_color=True)
    bbox = canvas.getbbox()
    if not bbox:
        return None
    cropped = canvas.crop(bbox)
    if cropped.height != target_px:
        width = max(1, int(round(cropped.width * target_px / cropped.height)))
        cropped = cropped.resize((width, target_px), Image.LANCZOS)
    try:
        cropped.save(cache_path)
    except Exception:
        pass
    return cropped


# ──────────────────────────────────────────────────────────────────────────────
# Overlay planning
# ──────────────────────────────────────────────────────────────────────────────
class EmojiOverlay:
    __slots__ = ("emoji", "start", "end", "x", "y", "size", "png_path")

    def __init__(self, emoji, start, end, x, y, size, png_path):
        self.emoji = emoji
        self.start = start
        self.end = end
        self.x = x
        self.y = y
        self.size = size
        self.png_path = png_path

    def __repr__(self):  # pragma: no cover - debugging aid
        return (f"EmojiOverlay({self.emoji!r}, {self.start:.2f}-{self.end:.2f}, "
                f"x={self.x}, y={self.y}, size={self.size})")


def emoji_overlay_supported(fonts_dir):
    """True when we can actually burn real colour emoji."""
    if not (_PIL_OK and _FT_OK):
        return False
    return os.path.exists(os.path.join(fonts_dir, COLOR_EMOJI_FILE))


def plan_emoji_overlays(ass_path, fonts_dir, play_res_x=1080, play_res_y=1920,
                        ffmpeg_bin=None, job_id=None, max_overlays=400):
    """Turn the emoji placeholders inside a generated .ass into overlay events.

    Returns a list of :class:`EmojiOverlay` (empty list = nothing to do, caller
    should keep the plain ASS result).
    """
    if not emoji_overlay_supported(fonts_dir):
        return []

    styles, dialogues = parse_ass_file(ass_path)
    if not dialogues:
        return []

    metrics_cache = {}

    def metrics_for(font_family, bold):
        cache_key = (font_family.lower(), bool(bold))
        if cache_key in metrics_cache:
            return metrics_cache[cache_key]
        if font_family.strip().lower() in _EMOJI_FAMILIES:
            resolved = {"path": os.path.join(fonts_dir, MONO_EMOJI_FILE), "index": 0}
            if not os.path.exists(resolved["path"]):
                resolved = None
        else:
            resolved = resolve_libass_font(font_family, bold, fonts_dir,
                                           ffmpeg_bin=ffmpeg_bin, job_id=job_id)
        value = None
        if resolved:
            try:
                value = FontMetrics(resolved["path"], resolved["index"])
            except Exception:
                value = None
        metrics_cache[cache_key] = value
        return value

    overlays = []
    for dialogue in dialogues:
        style = styles.get(dialogue["style"])
        if not style:
            continue  # watermark badges etc. never carry emoji
        if style["alignment"] != 2:
            continue  # only bottom-anchored styles are supported
        text = dialogue["text"]
        if not EMOJI_RE.search(text):
            continue

        runs = split_runs(text, style["font"], style["size"])
        text_metrics = metrics_for(style["font"], style["bold"])
        if text_metrics is None:
            continue

        # Measure the whole line exactly like libass does so we know where the
        # transparent emoji slots land.
        total_width = 0.0
        measured = []
        for run in runs:
            family = run["font"]
            if family.strip().lower() in _EMOJI_FAMILIES:
                run_metrics = metrics_for(MONO_EMOJI_FAMILY, False) or text_metrics
            else:
                run_metrics = metrics_for(family, style["bold"]) or text_metrics
            measured.append((total_width, run, run_metrics))
            total_width += run_metrics.advance(run["text"], run["size"])

        if total_width <= 0 or total_width > play_res_x - 8:
            continue  # would wrap — leave the plain ASS result untouched

        line_left = (play_res_x - total_width) / 2.0
        bottom_y = play_res_y - style["margin_v"]

        for run_start_x, run, run_metrics in measured:
            if not run["is_emoji"] or not run["visible"]:
                continue
            run_size = run["size"]
            for match in EMOJI_RE.finditer(run["text"]):
                prefix = run["text"][:match.start()]
                slot_x = line_left + run_start_x + run_metrics.advance(prefix, run_size)
                slot_w = run_metrics.advance(match.group(1), run_size)
                emoji = strip_variation_selectors(match.group(1))

                # Match the *text* em size (not the emoji font's, which is much
                # larger) so the emoji sits naturally next to the words.
                em_px = text_metrics.em_px(run_size) * EMOJI_SIZE_SCALE
                baseline = text_metrics.baseline_from_bottom(run_size, bottom_y)

                png = render_color_emoji(emoji, em_px, fonts_dir)
                if png is None:
                    continue

                draw_x = slot_x + (slot_w - png.width) / 2.0
                draw_y = baseline - png.height
                overlays.append(EmojiOverlay(
                    emoji=emoji,
                    start=dialogue["start"],
                    end=dialogue["end"],
                    x=int(round(draw_x)),
                    y=int(round(draw_y)),
                    size=int(png.width),
                    png_path=_write_overlay_png(png, emoji, int(round(em_px))),
                ))
                if len(overlays) >= max_overlays:
                    return _merge_overlays(overlays)

    return _merge_overlays(overlays)


def _write_overlay_png(image, emoji, size_px):
    digest = hashlib.sha1(f"{emoji}|{size_px}".encode("utf-8")).hexdigest()[:16]
    path = os.path.join(_emoji_cache_dir(), f"ov_{digest}.png")
    if not os.path.exists(path):
        try:
            image.save(path)
        except Exception:
            return None
    return path


def _merge_overlays(overlays):
    """Collapse consecutive identical placements so we emit fewer ffmpeg filters."""
    merged = []
    for item in overlays:
        if merged:
            prev = merged[-1]
            if (prev.png_path == item.png_path and prev.x == item.x and prev.y == item.y
                    and item.start - prev.end < 0.02):
                prev.end = max(prev.end, item.end)
                continue
        merged.append(item)
    return merged


# ──────────────────────────────────────────────────────────────────────────────
# ffmpeg overlay chain
# ──────────────────────────────────────────────────────────────────────────────
def build_overlay_graph(overlays, base_label="[vsub]", first_input_index=1):
    """Build ``(filter_string, input_args, final_label)`` for the emoji overlays.

    One ffmpeg input per *unique PNG*, fanned out with ``split`` so a 60s clip
    stays at a handful of decoded images instead of hundreds.
    """
    if not overlays:
        return "", [], base_label

    by_png = {}
    for overlay in overlays:
        if not overlay.png_path:
            continue
        by_png.setdefault(overlay.png_path, []).append(overlay)
    if not by_png:
        return "", [], base_label

    input_args = []
    chains = []
    current = base_label
    input_index = first_input_index
    label_no = 0

    for png_path, items in by_png.items():
        input_args += ["-loop", "1", "-i", png_path]
        stream = f"[{input_index}:v]"
        if len(items) == 1:
            sources = [stream]
        else:
            split_labels = "".join(f"[em{label_no}_{i}]" for i in range(len(items)))
            chains.append(f"{stream}split={len(items)}{split_labels}")
            sources = [f"[em{label_no}_{i}]" for i in range(len(items))]

        for src, overlay in zip(sources, items):
            out_label = f"[ov{label_no}]"
            chains.append(
                f"{current}{src}overlay=x={overlay.x}:y={overlay.y}"
                f":enable='between(t,{overlay.start:.3f},{overlay.end:.3f})'"
                f":eof_action=pass:format=auto{out_label}"
            )
            current = out_label
            label_no += 1
        input_index += 1

    return ";".join(chains), input_args, current
