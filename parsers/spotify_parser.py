"""
EXPOSED — Spotify Parser
Reads Spotify streaming history export and extracts behavioral signals.
Input:  StreamingHistory*.json (from Spotify data export)
Output: spotify_signals.json
"""

import json
import os
import glob
from collections import defaultdict
from datetime import datetime


def load_spotify_files(data_dir: str) -> list:
    """
    Load Spotify streaming history JSON files from export directory.
    Supports both formats:
      - Old:      StreamingHistory0.json, StreamingHistory1.json
      - Extended: Streaming_History_Audio_2025.json, Streaming_History_Audio_2025_1.json
    Video history files are intentionally skipped.
    """
    patterns = [
        "StreamingHistory*.json",
        "Streaming_History_Audio*.json",
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(data_dir, p)))
    files = sorted(set(files))

    if not files:
        raise FileNotFoundError(f"No streaming history files found in {data_dir}")

    all_entries = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            all_entries.extend(json.load(fh))

    print(f"Loaded {len(all_entries)} plays from {len(files)} file(s)")
    return all_entries


def normalize_entry(entry: dict) -> dict | None:
    """
    Normalize an entry from either old or extended Spotify export format
    into a common shape: {endTime, msPlayed, trackName, artistName}
    """
    # Extended format (ts, ms_played, master_metadata_track_name, ...)
    if "ts" in entry:
        ts = entry.get("ts")  # e.g. "2025-01-14T01:22:33Z"
        if not ts:
            return None
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None
        return {
            "endTime":    dt.strftime("%Y-%m-%d %H:%M"),
            "msPlayed":   entry.get("ms_played", 0),
            "trackName":  entry.get("master_metadata_track_name") or "Unknown",
            "artistName": entry.get("master_metadata_album_artist_name") or "Unknown",
            "incognito":  bool(entry.get("incognito_mode", False)),
            "skippedFlag": entry.get("skipped"),  # None for old format, True/False for extended
        }

    # Old format (endTime, msPlayed, trackName, artistName) — already normalized
    if "endTime" in entry:
        return {
            "endTime":    entry.get("endTime"),
            "msPlayed":   entry.get("msPlayed", 0),
            "trackName":  entry.get("trackName", "Unknown"),
            "artistName": entry.get("artistName", "Unknown"),
            "incognito":  False,
            "skippedFlag": None,
        }

    return None


def parse_entries(entries: list) -> dict:
    """Extract behavioral signals from raw streaming entries."""

    # ── counters ──────────────────────────────────────────────
    hourly_plays      = defaultdict(int)   # {0-23: count}
    daily_plays       = defaultdict(int)   # {Mon-Sun: count}
    track_plays       = defaultdict(int)   # {track_name: count}
    artist_plays      = defaultdict(int)   # {artist_name: count}
    ms_played_by_hour = defaultdict(int)   # {0-23: ms}
    sessions          = []                 # list of session dicts
    total_ms          = 0
    skipped           = 0                  # plays under 30s (excluded from analysis)
    incognito_plays   = 0                  # real incognito_mode=true count
    manual_skip_flag_count = 0             # Spotify's own skipped=true flag (manual fwdbtn/backbtn) — tracked separately, not used for exclusion

    # session detection — gap > 30 min = new session
    SESSION_GAP_MS = 30 * 60 * 1000
    current_session_start = None
    current_session_ms    = 0
    last_end_ts           = None

    for raw_entry in entries:
        entry = normalize_entry(raw_entry)
        if entry is None:
            continue

        try:
            end_time = datetime.strptime(entry["endTime"], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            continue

        ms = entry.get("msPlayed", 0)
        track  = entry.get("trackName", "Unknown")
        artist = entry.get("artistName", "Unknown")
        hour   = end_time.hour
        day    = end_time.strftime("%A")

        if entry.get("incognito"):
            incognito_plays += 1
        if entry.get("skippedFlag"):
            manual_skip_flag_count += 1

        # exclusion from analysis uses duration — under 30s means it wasn't really "listened to"
        if ms < 30_000:
            skipped += 1
            continue

        total_ms           += ms
        hourly_plays[hour] += 1
        daily_plays[day]   += 1
        track_plays[track] += 1
        artist_plays[artist] += 1
        ms_played_by_hour[hour] += ms

        # session tracking
        if last_end_ts is None or (end_time.timestamp()*1000 - last_end_ts) > SESSION_GAP_MS:
            if current_session_start:
                sessions.append({
                    "start_hour": current_session_start.hour,
                    "duration_min": round(current_session_ms / 60_000, 1)
                })
            current_session_start = end_time
            current_session_ms    = ms
        else:
            current_session_ms += ms

        last_end_ts = end_time.timestamp() * 1000

    if current_session_start:
        sessions.append({
            "start_hour": current_session_start.hour,
            "duration_min": round(current_session_ms / 60_000, 1)
        })

    # ── derived metrics ───────────────────────────────────────

    total_plays = sum(hourly_plays.values())

    # late night = 22:00 – 02:59
    late_night_hours = {22, 23, 0, 1, 2}
    late_night_plays = sum(hourly_plays[h] for h in late_night_hours)
    late_night_pct   = round(late_night_plays / total_plays * 100, 1) if total_plays else 0

    # peak hour
    peak_hour = max(hourly_plays, key=hourly_plays.get) if hourly_plays else 0

    # binge sessions (>60 min)
    binge_sessions = [s for s in sessions if s["duration_min"] >= 60]
    avg_session_min = round(
        sum(s["duration_min"] for s in sessions) / len(sessions), 1
    ) if sessions else 0
    late_night_sessions = [s for s in sessions if s["start_hour"] in late_night_hours]

    # repeat obsession — tracks played 5+ times
    repeat_tracks = {t: c for t, c in track_plays.items() if c >= 5}

    # top artists / tracks
    top_artists = sorted(artist_plays.items(), key=lambda x: x[1], reverse=True)[:10]
    top_tracks  = sorted(track_plays.items(),  key=lambda x: x[1], reverse=True)[:10]

    # solitary listening index (proxy: late-night solo %)
    # True shared data needs Spotify social API; we use late-night as proxy
    solitary_index = late_night_pct

    # hourly distribution (normalized 0-1 for dashboard heatmap)
    max_h = max(hourly_plays.values()) if hourly_plays else 1
    hourly_normalized = {str(h): round(hourly_plays[h] / max_h, 3) for h in range(24)}

    # weekly distribution
    days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    daily_normalized = {d: daily_plays.get(d, 0) for d in days_order}

    # ── assemble signals ──────────────────────────────────────
    signals = {
        "platform": "spotify",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_plays":        total_plays,
            "total_hours_played": round(total_ms / 3_600_000, 1),
            "total_sessions":     len(sessions),
            "skipped_tracks":     skipped,
            "unique_tracks":      len(track_plays),
            "unique_artists":     len(artist_plays),
        },
        "constructs": {
            "late_night_frequency": {
                "value":       late_night_pct,
                "unit":        "percent of plays",
                "description": "Percentage of total plays occurring between 10pm and 3am",
                "evidence": [
                    f"{late_night_plays} plays between 10pm–3am out of {total_plays} total",
                    f"Peak activity hour: {peak_hour}:00",
                    f"{len(late_night_sessions)} sessions started during late-night window",
                ]
            },
            "solitary_listening_index": {
                "value":       round(solitary_index, 1),
                "unit":        "percent",
                "description": "Proxy for solo listening based on late-night non-social usage patterns",
                "evidence": [
                    f"{late_night_plays} plays in non-social late-night window",
                    f"{incognito_plays} plays occurred in Spotify Private/Incognito Mode" if incognito_plays else "0 plays in Spotify Private/Incognito Mode — privacy achieved through timing, not the platform's privacy feature",
                    f"{len(repeat_tracks)} tracks replayed 5+ times — marker of private obsessive listening",
                ]
            },
            "mood_dependency_rate": {
                "value":       round(len(binge_sessions) / len(sessions) * 100, 1) if sessions else 0,
                "unit":        "percent of sessions",
                "description": "Proportion of sessions classified as emotional binge (>60 min continuous)",
                "evidence": [
                    f"{len(binge_sessions)} binge sessions (>60 min) out of {len(sessions)} total",
                    f"Average session length: {avg_session_min} minutes",
                    f"Average late-night session length: {round(sum(s['duration_min'] for s in late_night_sessions)/len(late_night_sessions),1) if late_night_sessions else 0} minutes",
                ]
            },
            "repeat_obsession_score": {
                "value":       len(repeat_tracks),
                "unit":        "tracks",
                "description": "Number of tracks played 5+ times — indicates unresolved emotional loops",
                "evidence": [
                    f"{len(repeat_tracks)} tracks played 5 or more times",
                    f"Top repeat: '{top_tracks[0][0]}' — {top_tracks[0][1]} plays" if top_tracks else "N/A",
                ]
            },
        },
        "distributions": {
            "hourly_normalized": hourly_normalized,
            "daily_plays":       daily_normalized,
            "top_artists":       top_artists,
            "top_tracks":        top_tracks[:5],
        },
        "raw_counts": {
            "hourly_plays": {str(k): v for k, v in hourly_plays.items()},
            "late_night_plays": late_night_plays,
            "binge_sessions":   len(binge_sessions),
            "peak_hour":        peak_hour,
            "incognito_plays":  incognito_plays,
            "manual_skips":     manual_skip_flag_count,
        }
    }

    return signals


def run(data_dir: str, output_path: str = "spotify_signals.json"):
    entries = load_spotify_files(data_dir)
    signals = parse_entries(entries)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2)

    print(f"\n✓ Spotify signals extracted → {output_path}")
    print(f"  Total plays:      {signals['summary']['total_plays']}")
    print(f"  Hours listened:   {signals['summary']['total_hours_played']}h")
    print(f"  Late-night freq:  {signals['constructs']['late_night_frequency']['value']}%")
    print(f"  Repeat tracks:    {signals['constructs']['repeat_obsession_score']['value']}")
    return signals


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    out      = sys.argv[2] if len(sys.argv) > 2 else "spotify_signals.json"
    run(data_dir, out)
