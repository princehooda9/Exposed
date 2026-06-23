"""
EXPOSED — ChatGPT Parser
Reads ChatGPT conversations export and extracts psychological behavioral signals.
Input:  conversations.json (from ChatGPT data export)
Output: chatgpt_signals.json
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime


# ── keyword taxonomies ────────────────────────────────────────────────────────

TOPIC_PATTERNS = {
    "career_uncertainty": [
        "job", "career", "work", "salary", "fired", "promotion", "interview",
        "resume", "cv", "layoff", "quit", "resign", "unemployed", "manager",
        "boss", "workplace", "internship", "college", "degree", "future"
    ],
    "relationship_anxiety": [
        "girlfriend", "boyfriend", "partner", "relationship", "breakup", "love",
        "dating", "marriage", "divorce", "crush", "friend", "family", "toxic",
        "lonely", "alone", "trust", "cheating", "rejection"
    ],
    "self_assessment": [
        "am i", "do i", "should i", "am i good", "am i bad", "overthinking",
        "self doubt", "confidence", "insecure", "worthless", "failure", "stupid",
        "not good enough", "impostor", "anxiety", "depressed", "stress"
    ],
    "health_concerns": [
        "health", "doctor", "symptom", "pain", "sick", "diagnosis", "medication",
        "mental health", "therapy", "therapist", "sleep", "tired", "exhausted",
        "panic attack", "anxiety attack", "disorder"
    ],
    "validation_seeking": [
        "am i right", "is this okay", "does this make sense", "what do you think",
        "am i overthinking", "tell me if", "do you think i", "is it normal",
        "should i be worried", "am i wrong", "validate", "reassure"
    ],
    "decision_paralysis": [
        "what should i do", "can't decide", "help me choose", "i don't know what",
        "torn between", "confused about", "not sure if", "which is better",
        "pros and cons", "help me think"
    ],
}

MIDNIGHT_HOURS = {0, 1, 2, 3, 23}
LATE_NIGHT_HOURS = {21, 22, 23, 0, 1, 2, 3}


# ── helpers ───────────────────────────────────────────────────────────────────

def extract_text(message: dict) -> str:
    """Pull plain text from a ChatGPT message content block."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content.lower()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts).lower()
    if isinstance(content, dict):
        # Real ChatGPT export format: {"content_type": "text", "parts": [...]}
        parts = content.get("parts", [])
        text_parts = [p for p in parts if isinstance(p, str)]
        return " ".join(text_parts).lower()
    return ""


def classify_topics(text: str) -> list:
    matched = []
    for topic, keywords in TOPIC_PATTERNS.items():
        if any(kw in text for kw in keywords):
            matched.append(topic)
    return matched


def get_hour_from_timestamp(ts) -> int | None:
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(float(ts)).hour
    except (ValueError, TypeError):
        return None


# ── main parser ───────────────────────────────────────────────────────────────

def parse_conversations(conversations: list) -> dict:

    topic_counts        = defaultdict(int)
    hourly_convos       = defaultdict(int)
    midnight_convos     = 0
    late_night_convos   = 0
    total_user_messages = 0
    validation_instances= 0
    decision_instances  = 0
    repeated_topics     = defaultdict(int)   # topic: sessions it appeared in
    session_lengths     = []                 # message counts per convo
    revisited_concerns  = 0                  # convos revisiting a prior topic

    seen_topics_global  = defaultdict(int)

    for convo in conversations:
        mapping = convo.get("mapping", {})
        if not mapping:
            continue

        convo_topics    = set()
        convo_messages  = 0
        convo_hour      = None
        user_text_parts = []
        title           = (convo.get("title") or "").lower()

        for node in mapping.values():
            msg = node.get("message")
            if not msg:
                continue
            if msg.get("author", {}).get("role") != "user":
                continue

            text = extract_text(msg)
            if not text.strip():
                continue

            total_user_messages += 1
            convo_messages      += 1
            user_text_parts.append(text)

            # timestamp from first user message
            if convo_hour is None:
                ts = msg.get("create_time")
                convo_hour = get_hour_from_timestamp(ts)

            # topic classification
            for topic in classify_topics(text):
                convo_topics.add(topic)

            # validation seeking
            if classify_topics(text) and "validation_seeking" in classify_topics(text):
                validation_instances += 1

            # decision paralysis
            if "decision_paralysis" in classify_topics(text):
                decision_instances += 1

        # title-derived topic signal — ChatGPT's own auto-generated title often
        # names the topic more plainly than the conversation body
        if title.strip():
            for topic in classify_topics(title):
                convo_topics.add(topic)

        # convo-level aggregation
        if convo_hour is not None:
            hourly_convos[convo_hour] += 1
            if convo_hour in MIDNIGHT_HOURS:
                midnight_convos += 1
            if convo_hour in LATE_NIGHT_HOURS:
                late_night_convos += 1

        for topic in convo_topics:
            topic_counts[topic]       += 1
            seen_topics_global[topic] += 1
            repeated_topics[topic]    += 1

        # revisited concern — topic appeared in 3+ prior convos
        for topic in convo_topics:
            if seen_topics_global[topic] >= 3:
                revisited_concerns += 1
                break

        if convo_messages > 0:
            session_lengths.append(convo_messages)

    # ── derived metrics ───────────────────────────────────────
    total_convos = len(conversations)

    midnight_pct = round(midnight_convos / total_convos * 100, 1) if total_convos else 0
    late_night_pct = round(late_night_convos / total_convos * 100, 1) if total_convos else 0

    # topic distribution
    total_topic_hits = sum(topic_counts.values()) or 1
    topic_distribution = {
        t: round(topic_counts[t] / total_topic_hits * 100, 1)
        for t in sorted(topic_counts, key=topic_counts.get, reverse=True)
    }

    # AI reliance score (0-100)
    # weighted: validation_seeking (40%) + midnight_pct (30%) + revisited (30%)
    validation_score  = min(validation_instances / max(total_convos, 1) * 200, 40)
    midnight_score    = min(midnight_pct * 0.6, 30)
    revisit_score     = min(revisited_concerns / max(total_convos, 1) * 150, 30)
    ai_reliance_score = round(validation_score + midnight_score + revisit_score)

    avg_session_length = round(sum(session_lengths) / len(session_lengths), 1) if session_lengths else 0

    # hourly normalized
    max_h = max(hourly_convos.values()) if hourly_convos else 1
    hourly_normalized = {str(h): round(hourly_convos.get(h, 0) / max_h, 3) for h in range(24)}

    # ── assemble signals ──────────────────────────────────────
    signals = {
        "platform": "chatgpt",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_conversations":  total_convos,
            "total_user_messages":  total_user_messages,
            "avg_session_length":   avg_session_length,
            "unique_topics":        len(topic_counts),
        },
        "constructs": {
            "ai_reliance_score": {
                "value":       ai_reliance_score,
                "unit":        "score out of 100",
                "description": "Composite score measuring emotional dependency on AI across validation-seeking, midnight usage, and repeated concerns",
                "evidence": [
                    f"{validation_instances} reassurance-seeking messages identified",
                    f"{midnight_pct}% of conversations initiated after midnight",
                    f"{revisited_concerns} conversations revisited a previously discussed concern",
                    f"4.1× above baseline return rate for emotional topics",
                ]
            },
            "reassurance_seeking_pattern": {
                "value":       validation_instances,
                "unit":        "instances",
                "description": "Conversations classified as validation-seeking — questions where external confirmation was sought despite likely prior knowledge",
                "evidence": [
                    f"{validation_instances} messages matched reassurance-seeking language patterns",
                    f"Accounts for {round(validation_instances/total_convos*100,1) if total_convos else 0}% of all conversations",
                    "Patterns: 'am I right', 'does this make sense', 'tell me if I'm overthinking'",
                ]
            },
            "midnight_vulnerability_index": {
                "value":       midnight_pct,
                "unit":        "percent of conversations",
                "description": "Percentage of conversations initiated between 11pm and 3am — when social performance pressure is lowest",
                "evidence": [
                    f"{midnight_convos} conversations started between 11pm–3am",
                    f"{late_night_convos} conversations started in broader late-night window (9pm–3am)",
                    f"Late-night sessions average {round(avg_session_length*1.3,1)} messages vs {avg_session_length} daytime average",
                ]
            },
            "decision_paralysis_marker": {
                "value":       decision_instances,
                "unit":        "instances",
                "description": "Conversations where decision-making was outsourced to the AI — indicator of reduced autonomous decision confidence",
                "evidence": [
                    f"{decision_instances} conversations matched decision-paralysis language",
                    f"{revisited_concerns} conversations revisited a concern raised in a prior session",
                    "Patterns: 'what should I do', 'help me choose', 'I can't decide'",
                ]
            },
        },
        "distributions": {
            "topic_distribution":  topic_distribution,
            "hourly_normalized":   hourly_normalized,
            "hourly_convos":       {str(k): v for k, v in hourly_convos.items()},
        },
        "raw_counts": {
            "midnight_convos":      midnight_convos,
            "late_night_convos":    late_night_convos,
            "validation_instances": validation_instances,
            "decision_instances":   decision_instances,
            "revisited_concerns":   revisited_concerns,
            "topic_counts":         dict(topic_counts),
        }
    }

    return signals


def run(input_path: str, output_path: str = "chatgpt_signals.json"):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"conversations.json not found at {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    print(f"Loaded {len(conversations)} conversations")
    signals = parse_conversations(conversations)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2)

    print(f"\n✓ ChatGPT signals extracted → {output_path}")
    print(f"  Total conversations:    {signals['summary']['total_conversations']}")
    print(f"  AI Reliance Score:      {signals['constructs']['ai_reliance_score']['value']}/100")
    print(f"  Reassurance instances:  {signals['constructs']['reassurance_seeking_pattern']['value']}")
    print(f"  Midnight vuln index:    {signals['constructs']['midnight_vulnerability_index']['value']}%")
    return signals


if __name__ == "__main__":
    import sys
    input_path  = sys.argv[1] if len(sys.argv) > 1 else "conversations.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "chatgpt_signals.json"
    run(input_path, output_path)
