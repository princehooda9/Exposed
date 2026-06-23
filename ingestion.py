"""
EXPOSED — File Ingestion
Accepts one or more uploaded .zip files, unzips in memory, auto-detects
which platform each archive belongs to based on filenames inside, and
routes contents to the correct parser.

Supports:
  - Spotify  (StreamingHistory*.json  /  Streaming_History_Audio*.json)
  - ChatGPT  (conversations.json)

Designed to be called from app.py with Streamlit's UploadedFile objects.
"""

import io
import json
import zipfile
from dataclasses import dataclass, field

from parsers.spotify_parser import parse_entries as parse_spotify_entries
from parsers.chatgpt_parser import parse_conversations as parse_chatgpt_conversations


# ── detection rules ───────────────────────────────────────────────────────────

SPOTIFY_FILENAME_HINTS = ("streaminghistory", "streaming_history_audio")
CHATGPT_FILENAME_HINTS = ("conversations.json",)


@dataclass
class IngestResult:
    platforms_found: list = field(default_factory=list)   # ["spotify", "chatgpt"]
    spotify_signals: dict | None = None
    chatgpt_signals: dict | None = None
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def _detect_platform(filename: str) -> str | None:
    name = filename.lower()
    if name.endswith(".json"):
        if any(hint in name for hint in SPOTIFY_FILENAME_HINTS):
            return "spotify"
        if any(hint in name for hint in CHATGPT_FILENAME_HINTS):
            return "chatgpt"
        # ChatGPT exports sometimes ship as just "conversations.json" inside
        # a dated folder — also catch loose matches
        if "conversation" in name:
            return "chatgpt"
    return None


def _extract_json_files_from_zip(uploaded_file) -> list[tuple[str, dict]]:
    """
    Returns list of (filename, parsed_json_content) for every .json file
    found anywhere inside the zip (including nested folders).
    """
    results = []
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # reset pointer in case streamlit needs to reread

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                if not info.filename.lower().endswith(".json"):
                    continue
                try:
                    with z.open(info) as f:
                        content = json.load(f)
                    results.append((info.filename, content))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
    except zipfile.BadZipFile:
        return []

    return results


def ingest_uploads(uploaded_files: list) -> IngestResult:
    """
    Main entry point. Pass a list of Streamlit UploadedFile objects
    (each expected to be a .zip from Spotify or ChatGPT).
    """
    result = IngestResult()

    spotify_raw_entries = []
    chatgpt_conversations = []

    for uploaded_file in uploaded_files:
        fname = uploaded_file.name.lower()

        if not fname.endswith(".zip"):
            result.warnings.append(f"Skipped '{uploaded_file.name}' — not a .zip file")
            continue

        json_files = _extract_json_files_from_zip(uploaded_file)

        if not json_files:
            result.warnings.append(f"No JSON files found inside '{uploaded_file.name}'")
            continue

        matched_any = False
        for inner_name, content in json_files:
            platform = _detect_platform(inner_name)

            if platform == "spotify" and isinstance(content, list):
                spotify_raw_entries.extend(content)
                matched_any = True

            elif platform == "chatgpt" and isinstance(content, list):
                chatgpt_conversations.extend(content)
                matched_any = True

        if not matched_any:
            result.warnings.append(
                f"'{uploaded_file.name}' did not match a known platform format"
            )

    # ── parse spotify ─────────────────────────────────────────────────────────
    if spotify_raw_entries:
        try:
            result.spotify_signals = parse_spotify_entries(spotify_raw_entries)
            result.platforms_found.append("spotify")
        except Exception as e:
            result.errors.append(f"Spotify parsing failed: {e}")

    # ── parse chatgpt ─────────────────────────────────────────────────────────
    if chatgpt_conversations:
        try:
            result.chatgpt_signals = parse_chatgpt_conversations(chatgpt_conversations)
            result.platforms_found.append("chatgpt")
        except Exception as e:
            result.errors.append(f"ChatGPT parsing failed: {e}")

    return result
