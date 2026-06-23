"""
EXPOSED — Profile Engine
Takes spotify_signals.json + chatgpt_signals.json
Makes 3 Gemini calls:
  1. Spotify profile
  2. ChatGPT profile
  3. Contrast / gap layer
Outputs: profiles.json
"""

import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # reads .env file in the project root if present

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL = os.environ.get("EXPOSED_MODEL", "gemini-2.5-flash")  # free tier model


# ── prompt builders ───────────────────────────────────────────────────────────

def build_spotify_prompt(signals: dict) -> str:
    c  = signals["constructs"]
    s  = signals["summary"]
    rd = signals["raw_counts"]
    return f"""
You are a behavioral data analyst writing a psychological profile for EXPOSED — 
a tool that shows users how platforms exploit their behavioral patterns.

Tone: clinical, evidence-backed, direct. No fluff. No therapy speak.
Every claim must reference a specific number from the data.
Write in second person ("You...").

SPOTIFY BEHAVIORAL SIGNALS:
- Total plays: {s['total_plays']}
- Total hours: {s['total_hours_played']}h
- Late-night frequency: {c['late_night_frequency']['value']}% of plays between 10pm–3am
- Peak activity hour: {rd['peak_hour']}:00
- Solitary listening index: {c['solitary_listening_index']['value']}%
- Mood dependency rate: {c['mood_dependency_rate']['value']}% of sessions are emotional binges (60+ min)
- Repeat obsession score: {c['repeat_obsession_score']['value']} tracks played 5+ times
- Binge sessions: {rd['binge_sessions']}
- Late-night plays: {rd['late_night_plays']}

TASK: Write exactly 3 sections as JSON:

{{
  "headline": "One punchy sentence — what Spotify has identified about this person. Max 20 words. Bold claim backed by data.",
  "findings": [
    "Finding 1 — specific behavioral signal with exact numbers from data",
    "Finding 2 — what Spotify did in response to that signal with numbers",
    "Finding 3 — the dependency loop this created with numbers",
    "Finding 4 — one more pattern from the data"
  ],
  "what_spotify_missed": [
    "Gap 1 — what the data suggests but Spotify's model failed to connect",
    "Gap 2 — a contradicting signal that reveals the model's blind spot"
  ],
  "confidence": 73
}}

Return only valid JSON. No markdown. No explanation.
""".strip()


def build_chatgpt_prompt(signals: dict) -> str:
    c  = signals["constructs"]
    s  = signals["summary"]
    rd = signals["raw_counts"]
    td = signals["distributions"]["topic_distribution"]
    return f"""
You are a behavioral data analyst writing a psychological profile for EXPOSED —
a tool that shows users how platforms exploit their behavioral patterns.

Tone: clinical, evidence-backed, direct. No fluff. No therapy speak.
Every claim must reference a specific number from the data.
Write in second person ("You...").

CHATGPT BEHAVIORAL SIGNALS:
- Total conversations: {s['total_conversations']}
- AI Reliance Score: {c['ai_reliance_score']['value']}/100
- Reassurance-seeking instances: {c['reassurance_seeking_pattern']['value']}
- Midnight vulnerability index: {c['midnight_vulnerability_index']['value']}% of convos after 11pm
- Decision paralysis instances: {c['decision_paralysis_marker']['value']}
- Revisited concerns: {rd['revisited_concerns']} convos returned to a prior unresolved topic
- Topic distribution: {json.dumps(td)}

TASK: Write exactly 3 sections as JSON:

{{
  "headline": "One punchy sentence — what ChatGPT has identified about this person. Max 20 words. Bold claim backed by data.",
  "findings": [
    "Finding 1 — specific pattern with exact numbers",
    "Finding 2 — what ChatGPT did in response with numbers",
    "Finding 3 — the dependency loop created with numbers",
    "Finding 4 — one more pattern from the data"
  ],
  "what_chatgpt_missed": [
    "Gap 1 — what the data suggests but ChatGPT's model failed to connect",
    "Gap 2 — a contradicting signal that reveals the model's blind spot"
  ],
  "confidence": 71
}}

Return only valid JSON. No markdown. No explanation.
""".strip()


def build_contrast_prompt(spotify: dict, chatgpt: dict) -> str:
    sc = spotify["constructs"]
    cc = chatgpt["constructs"]
    return f"""
You are a behavioral data analyst writing the contrast layer for EXPOSED —
the section that reveals what both platforms together know about a person that neither reveals alone.

Tone: clinical, measured, precise. The most uncomfortable section of the report.
Every claim references specific numbers. Second person ("You...").

SPOTIFY CONSTRUCTS:
- Late-night frequency: {sc['late_night_frequency']['value']}%
- Solitary listening index: {sc['solitary_listening_index']['value']}%
- Mood dependency rate: {sc['mood_dependency_rate']['value']}%

CHATGPT CONSTRUCTS:
- AI Reliance Score: {cc['ai_reliance_score']['value']}/100
- Reassurance-seeking: {cc['reassurance_seeking_pattern']['value']} instances
- Midnight vulnerability: {cc['midnight_vulnerability_index']['value']}%

TASK: Write the contrast layer as JSON:

{{
  "headline": "One sentence — what both platforms together reveal that neither shows alone. Max 25 words.",
  "spotify_sees": "2 sentences — what Spotify's data presents this person as",
  "chatgpt_sees": "2 sentences — what ChatGPT's data presents this person as",
  "the_gap": "3-4 sentences — the divergence between the two profiles. Clinical language. Specific numbers. What both platforms are exploiting.",
  "verdict": "4-5 sentences — the full cross-platform behavioral analysis. This is the typeout text. Make it land.",
  "final_sentence": "The single most uncomfortable true sentence about this person. Max 25 words. No hedging.",
  "divergence_confidence": 73
}}

Return only valid JSON. No markdown. No explanation.
""".strip()


# ── API calls ─────────────────────────────────────────────────────────────────

def call_gpt(prompt: str, label: str) -> dict:
    print(f"  Calling Gemini for {label}...")
    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw = (response.text or "").strip()
    # strip markdown fences if model adds them
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error for {label}: {e}")
        print(f"  Raw response: {raw[:200]}")
        return {"error": str(e), "raw": raw}


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    spotify_signals_path: str  = "spotify_signals.json",
    chatgpt_signals_path: str  = "chatgpt_signals.json",
    output_path: str           = "profiles.json",
):
    # load signals
    with open(spotify_signals_path, "r") as f:
        spotify = json.load(f)
    with open(chatgpt_signals_path, "r") as f:
        chatgpt = json.load(f)

    print("Generating profiles via GPT-4o...")

    spotify_profile  = call_gpt(build_spotify_prompt(spotify),   "Spotify profile")
    chatgpt_profile  = call_gpt(build_chatgpt_prompt(chatgpt),   "ChatGPT profile")
    contrast_profile = call_gpt(build_contrast_prompt(spotify, chatgpt), "Contrast layer")

    profiles = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "model":        MODEL,
        "spotify": {
            "signals":  spotify,
            "profile":  spotify_profile,
        },
        "chatgpt": {
            "signals":  chatgpt,
            "profile":  chatgpt_profile,
        },
        "contrast": contrast_profile,
    }

    with open(output_path, "w") as f:
        json.dump(profiles, f, indent=2)

    print(f"\n✓ Profiles generated → {output_path}")
    print(f"  Spotify headline:  {spotify_profile.get('headline','')[:60]}...")
    print(f"  ChatGPT headline:  {chatgpt_profile.get('headline','')[:60]}...")
    print(f"  Final sentence:    {contrast_profile.get('final_sentence','')[:60]}...")
    return profiles


if __name__ == "__main__":
    import sys
    run(
        spotify_signals_path = sys.argv[1] if len(sys.argv) > 1 else "spotify_signals.json",
        chatgpt_signals_path = sys.argv[2] if len(sys.argv) > 2 else "chatgpt_signals.json",
        output_path          = sys.argv[3] if len(sys.argv) > 3 else "profiles.json",
    )
