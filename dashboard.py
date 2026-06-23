"""
EXPOSED — Dashboard
Streamlit app. Reads profiles.json and renders the full dossier UI.

Run:
    streamlit run dashboard.py
"""

import json
import os
import time
import streamlit as st
from pathlib import Path
from pdf_report import get_pdf_bytes

CODE_VERSION = "v5-2026-06-21-pdf-header-hardcode-fix"
print(f"\n{'='*60}\nEXPOSED dashboard.py loaded — CODE_VERSION = {CODE_VERSION}\nFile path: {__file__}\n{'='*60}\n")

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EXPOSED",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.sidebar.caption(f"CODE_VERSION: {CODE_VERSION}")
st.sidebar.caption(f"Running from: {__file__}")

# ── global styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #07070f;
    color: #e8e6f0;
}

/* hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2rem 4rem 2rem; max-width: 900px; }

/* cards */
.card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 16px;
}
.card-cy { border-color: rgba(0,229,255,0.18); }
.card-pu { border-color: rgba(155,92,255,0.18); }
.card-rd { border-color: rgba(255,45,109,0.22); }

/* typography */
.mono     { font-family: 'Space Mono', monospace; }
.sec-tag  { font-family: 'Space Mono', monospace; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 10px; }
.cy       { color: #00e5ff; }
.pu       { color: #9b5cff; }
.rd       { color: #ff2d6d; }
.muted    { color: rgba(255,255,255,0.3); }

.headline { font-size: 20px; font-weight: 700; line-height: 1.4; margin-bottom: 14px; }

/* pills */
.pill     { display: inline-block; font-family: 'Space Mono', monospace; font-size: 10px; padding: 4px 10px; border-radius: 20px; margin: 3px; letter-spacing: 1px; }
.pill-cy  { background: rgba(0,229,255,0.08);  color: #00e5ff; border: 1px solid rgba(0,229,255,0.25); }
.pill-pu  { background: rgba(155,92,255,0.08); color: #9b5cff; border: 1px solid rgba(155,92,255,0.25); }
.pill-rd  { background: rgba(255,45,109,0.08); color: #ff2d6d; border: 1px solid rgba(255,45,109,0.25); }

/* bullets */
.bullet   { font-size: 13px; color: rgba(255,255,255,0.5); padding-left: 18px; position: relative; line-height: 1.8; margin-bottom: 8px; }
.bullet::before { content: '—'; position: absolute; left: 0; color: rgba(255,255,255,0.15); font-family: 'Space Mono', monospace; }
.bullet b { color: #e8e6f0; }

/* missed box */
.missed   { background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 14px; margin-top: 14px; }
.missed-title { font-family: 'Space Mono', monospace; font-size: 9px; letter-spacing: 2px; color: rgba(255,255,255,0.2); text-transform: uppercase; margin-bottom: 10px; }
.missed-item  { font-size: 12px; color: rgba(255,255,255,0.4); line-height: 1.7; margin-bottom: 6px; }

/* evidence cards */
.ev-card  { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 14px; margin-bottom: 10px; cursor: pointer; }
.ev-score { font-family: 'Space Mono', monospace; font-size: 28px; font-weight: 700; line-height: 1; }
.ev-label { font-size: 11px; color: rgba(255,255,255,0.35); margin-top: 4px; }
.ev-point { font-size: 11px; color: rgba(255,255,255,0.4); padding: 3px 0 3px 14px; position: relative; line-height: 1.6; }
.ev-point::before { content: '+'; position: absolute; left: 0; color: rgba(255,255,255,0.2); }

/* gap */
.gap-side { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px; }
.divergence { background: rgba(255,45,109,0.06); border: 1px solid rgba(255,45,109,0.2); border-radius: 10px; padding: 16px; margin: 14px 0; }

/* final sentence */
.final-sentence { font-size: 16px; font-style: italic; color: #e8e6f0; text-align: center; padding: 24px; line-height: 1.8; border-top: 1px solid rgba(255,255,255,0.07); margin-top: 16px; }

/* stat box */
.stat-box { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; text-align: center; }
.stat-n   { font-family: 'Space Mono', monospace; font-size: 28px; font-weight: 700; line-height: 1; }
.stat-l   { font-size: 9px; letter-spacing: 2px; color: rgba(255,255,255,0.25); margin-top: 6px; text-transform: uppercase; }

/* bar */
.bar-wrap { margin-bottom: 10px; }
.bar-label-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
.bar-label-text { font-size: 11px; color: rgba(255,255,255,0.35); }
.bar-pct-text   { font-family: 'Space Mono', monospace; font-size: 10px; color: rgba(255,255,255,0.25); }
.bar-track { height: 3px; background: rgba(255,255,255,0.05); border-radius: 2px; }
.bar-fill  { height: 3px; border-radius: 2px; }

/* download btn */
.dl-btn { width: 100%; padding: 16px; background: rgba(255,45,109,0.08); border: 1px solid rgba(255,45,109,0.3); border-radius: 12px; color: #ff2d6d; font-family: 'Space Mono', monospace; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; cursor: pointer; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def card(content_html: str, variant: str = "") -> None:
    cls = f"card card-{variant}" if variant else "card"
    st.markdown(f'<div class="{cls}">{content_html}</div>', unsafe_allow_html=True)


def pill(text: str, color: str = "cy") -> str:
    return f'<span class="pill pill-{color}">{text}</span>'


def bullet(text: str) -> str:
    return f'<div class="bullet">{text}</div>'


def bar_html(label: str, pct: float, color: str) -> str:
    return (f'<div class="bar-wrap"><div class="bar-label-row">'
            f'<span class="bar-label-text">{label}</span>'
            f'<span class="bar-pct-text">{pct}%</span></div>'
            f'<div class="bar-track"><div class="bar-fill" '
            f'style="width:{pct}%;background:{color}"></div></div></div>')


def heatmap_html(hourly: dict) -> str:
    cells = ""
    for h in range(24):
        v = hourly.get(str(h), 0)
        r = int(10 + v * 200)
        g = int(10 + v * 30)
        b = int(40 + v * 60)
        cells += f'<div style="height:16px;border-radius:2px;background:rgb({r},{g},{b})"></div>'
    labels = ('<span class="muted mono" style="font-size:9px">12AM</span>'
              '<span class="muted mono" style="font-size:9px">6AM</span>'
              '<span class="muted mono" style="font-size:9px">12PM</span>'
              '<span class="muted mono" style="font-size:9px">6PM</span>'
              '<span class="rd mono" style="font-size:9px">11PM</span>')
    return (f'<div style="display:grid;grid-template-columns:repeat(24,1fr);gap:2px;margin:8px 0">{cells}</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:4px">{labels}</div>')


def load_profiles(path: str) -> dict | None:
    if not Path(path).exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── screens ───────────────────────────────────────────────────────────────────

def render_header(profiles: dict):
    has_spotify = "spotify" in profiles
    has_chatgpt = "chatgpt" in profiles
    platform_count = sum([has_spotify, has_chatgpt])
    contrast = profiles.get("contrast", {})

    data_points = 0
    if has_spotify:
        data_points += profiles["spotify"]["signals"]["summary"]["total_plays"]
    if has_chatgpt:
        data_points += profiles["chatgpt"]["signals"]["summary"]["total_conversations"]

    findings_count = 0
    for plat in ("spotify", "chatgpt"):
        if plat in profiles:
            findings_count += len(profiles[plat]["profile"].get("findings", []))

    platform_chips = ""
    if has_spotify:
        sp_sig = profiles["spotify"]["signals"]
        platform_chips += (
            '<div style="display:flex;align-items:center;gap:10px;background:rgba(255,255,255,0.02);'
            'border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 14px">'
            '<div style="width:3px;height:28px;background:#00e5ff;border-radius:2px"></div>'
            '<div><div class="cy mono" style="font-size:11px;font-weight:700;letter-spacing:1px">SPOTIFY</div>'
            f'<div class="muted" style="font-size:9px;letter-spacing:1px;text-transform:uppercase">'
            f'{sp_sig["summary"]["total_plays"]} plays · {sp_sig["summary"]["total_hours_played"]}h</div></div></div>'
        )
    if has_chatgpt:
        gp_sig = profiles["chatgpt"]["signals"]
        platform_chips += (
            '<div style="display:flex;align-items:center;gap:10px;background:rgba(255,255,255,0.02);'
            'border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 14px">'
            '<div style="width:3px;height:28px;background:#9b5cff;border-radius:2px"></div>'
            '<div><div class="pu mono" style="font-size:11px;font-weight:700;letter-spacing:1px">CHATGPT</div>'
            f'<div class="muted" style="font-size:9px;letter-spacing:1px;text-transform:uppercase">'
            f'{gp_sig["summary"]["total_conversations"]} conversations</div></div></div>'
        )

    confidence_stat = f"{contrast.get('divergence_confidence', 73)}%" if platform_count == 2 else "—"

    card(f"""
    <div class="sec-tag muted">EXPOSED · Subject File</div>
    <div class="headline mono" style="font-size:22px;letter-spacing:1px">SUBJECT FILE — USER_{hash(profiles["generated_at"]) % 9999:04d}</div>
    <div class="muted mono" style="font-size:9px;letter-spacing:2px;margin-bottom:22px;text-transform:uppercase">
      Generated: {profiles["generated_at"][:10]} · Platforms: {platform_count} · Classification: Personal
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">
      <div class="stat-box"><div class="stat-n cy">{platform_count}</div><div class="stat-l">Platforms</div></div>
      <div class="stat-box"><div class="stat-n pu">{findings_count}</div><div class="stat-l">Findings</div></div>
      <div class="stat-box"><div class="stat-n rd">{data_points}</div><div class="stat-l">Data points</div></div>
      <div class="stat-box"><div class="stat-n">{confidence_stat}</div><div class="stat-l">Confidence</div></div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      {platform_chips}
    </div>
    """)


def render_spotify(profiles: dict):
    sig  = profiles["spotify"]["signals"]
    prof = profiles["spotify"]["profile"]
    c    = sig["constructs"]
    dist = sig["distributions"]

    findings_html = "".join(bullet(f"<b>{i+1}.</b> {f}") for i, f in enumerate(prof.get("findings", [])))
    missed_html   = "".join(f'<div class="missed-item">→ {m}</div>' for m in prof.get("what_spotify_missed", []))

    pills_html = (
        pill(f"Solitary Listening Index: {c['solitary_listening_index']['value']}%", "cy") +
        pill(f"Late-Night Frequency: {c['late_night_frequency']['value']}%", "cy") +
        pill(f"Mood Dependency Rate: {c['mood_dependency_rate']['value']}%", "rd") +
        pill(f"Repeat Obsession: {c['repeat_obsession_score']['value']} tracks", "pu")
    )

    topic_bars = ""
    top_artists = dist.get("top_artists", [])[:5]
    artist_colors = ["#00e5ff", "#9b5cff", "rgba(0,229,255,0.5)", "rgba(255,255,255,0.2)", "rgba(255,255,255,0.1)"]
    max_count = top_artists[0][1] if top_artists else 1
    for i, (artist, count) in enumerate(top_artists):
        pct = round(count / max_count * 100, 1)
        topic_bars += bar_html(artist, pct, artist_colors[i % len(artist_colors)])

    card(f"""
    <div class="sec-tag cy">Spotify · Behavioral Profile</div>
    <div class="headline">{prof.get("headline", "")}</div>
    <div style="margin-bottom:16px">{pills_html}</div>
    {findings_html}
    <div style="margin-top:16px">
      <div class="sec-tag muted">Usage heatmap — hourly</div>
      {heatmap_html(dist['hourly_normalized'])}
    </div>
    <div style="margin-top:16px">{topic_bars}</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px">
      <div class="stat-box"><div class="stat-n cy">{sig['raw_counts']['late_night_plays']}</div><div class="stat-l">Late-night plays</div></div>
      <div class="stat-box"><div class="stat-n cy">{sig['raw_counts']['peak_hour']}:00</div><div class="stat-l">Peak hour</div></div>
      <div class="stat-box"><div class="stat-n rd">{sig['raw_counts']['binge_sessions']}</div><div class="stat-l">Binge sessions</div></div>
    </div>
    <div class="missed">
      <div class="missed-title">What Spotify missed</div>
      {missed_html}
    </div>
    """, "cy")


def render_chatgpt(profiles: dict):
    sig  = profiles["chatgpt"]["signals"]
    prof = profiles["chatgpt"]["profile"]
    c    = sig["constructs"]
    dist = sig["distributions"]
    rd   = sig["raw_counts"]

    findings_html = "".join(bullet(f"<b>{i+1}.</b> {f}") for i, f in enumerate(prof.get("findings", [])))
    missed_html   = "".join(f'<div class="missed-item">→ {m}</div>' for m in prof.get("what_chatgpt_missed", []))

    pills_html = (
        pill(f"AI Reliance Score: {c['ai_reliance_score']['value']}/100", "pu") +
        pill(f"Reassurance Seeking: {c['reassurance_seeking_pattern']['value']} instances", "pu") +
        pill(f"Midnight Vulnerability: {c['midnight_vulnerability_index']['value']}%", "rd") +
        pill(f"Decision Paralysis: {c['decision_paralysis_marker']['value']} instances", "pu")
    )

    topic_bars = ""
    td = dist.get("topic_distribution", {})
    colors = {"career_uncertainty":"#ff2d6d","relationship_anxiety":"#9b5cff",
              "self_assessment":"rgba(155,92,255,0.6)","health_concerns":"rgba(255,45,109,0.5)",
              "validation_seeking":"rgba(155,92,255,0.4)","decision_paralysis":"rgba(255,255,255,0.15)"}
    for topic, pct in list(td.items())[:5]:
        label = topic.replace("_", " ").title()
        topic_bars += bar_html(label, pct, colors.get(topic, "#555"))

    card(f"""
    <div class="sec-tag pu">ChatGPT · Psychological Profile</div>
    <div class="headline">{prof.get("headline", "")}</div>
    <div style="margin-bottom:16px">{pills_html}</div>
    {findings_html}
    <div style="margin-top:16px">
      <div class="sec-tag muted">Conversation heatmap — hourly</div>
      {heatmap_html(dist['hourly_normalized'])}
    </div>
    <div style="margin-top:16px">{topic_bars}</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px">
      <div class="stat-box"><div class="stat-n pu">{c['ai_reliance_score']['value']}</div><div class="stat-l">Reliance score</div></div>
      <div class="stat-box"><div class="stat-n rd">{rd['midnight_convos']}</div><div class="stat-l">Midnight convos</div></div>
      <div class="stat-box"><div class="stat-n pu">{rd['revisited_concerns']}</div><div class="stat-l">Revisited concerns</div></div>
    </div>
    <div class="missed">
      <div class="missed-title">What ChatGPT missed</div>
      {missed_html}
    </div>
    """, "pu")


def render_evidence(profiles: dict):
    has_spotify = "spotify" in profiles
    has_chatgpt = "chatgpt" in profiles
    if not (has_spotify or has_chatgpt):
        return

    def ev_card(score, label, evidence_list, pill_color):
        evs = "".join(f'<div class="ev-point">{e}</div>' for e in evidence_list)
        with st.expander(f"{score}  —  {label}"):
            st.markdown(
                f'<div style="padding:4px 0">{pill(label, pill_color)}'
                f'<div style="margin-top:12px">{evs}</div></div>',
                unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="sec-tag muted">Evidence Explorer — expand any construct to see proof</div>', unsafe_allow_html=True)
    if has_spotify:
        sp_c = profiles["spotify"]["signals"]["constructs"]
        ev_card(f"{sp_c['solitary_listening_index']['value']}%", "Solitary Listening Index", sp_c['solitary_listening_index']['evidence'], "cy")
        ev_card(f"{sp_c['mood_dependency_rate']['value']}%",     "Mood Dependency Rate",      sp_c['mood_dependency_rate']['evidence'],     "cy")
    if has_chatgpt:
        gp_c = profiles["chatgpt"]["signals"]["constructs"]
        ev_card(f"{gp_c['ai_reliance_score']['value']}/100",       "AI Reliance Score",            gp_c['ai_reliance_score']['evidence'],         "pu")
        ev_card(f"{gp_c['reassurance_seeking_pattern']['value']}", "Reassurance Seeking Pattern",  gp_c['reassurance_seeking_pattern']['evidence'],"pu")
    st.markdown('</div>', unsafe_allow_html=True)


def render_gap(profiles: dict):
    # the contrast/gap layer only makes sense with both platforms
    if "spotify" not in profiles or "chatgpt" not in profiles:
        return
    contrast = profiles.get("contrast", {})

    card(f"""
    <div class="sec-tag rd">The Gap · Cross-Platform Divergence</div>
    <div class="headline">{contrast.get("headline", "Both platforms independently mapped the same split in you.")}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
      <div class="gap-side">
        <div class="sec-tag cy" style="margin-bottom:8px">What Spotify sees</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.45);line-height:1.7">{contrast.get("spotify_sees","")}</div>
      </div>
      <div class="gap-side">
        <div class="sec-tag pu" style="margin-bottom:8px">What ChatGPT sees</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.45);line-height:1.7">{contrast.get("chatgpt_sees","")}</div>
      </div>
    </div>
    <div class="divergence">
      <div class="sec-tag rd" style="margin-bottom:6px">Divergence finding · Confidence: {contrast.get("divergence_confidence",73)}%</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.55);line-height:1.8">{contrast.get("the_gap","")}</div>
    </div>
    <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.9;border-left:2px solid rgba(255,45,109,0.3);padding-left:16px">
      {contrast.get("verdict","")}
    </div>
    <div class="final-sentence">"{contrast.get("final_sentence","")}"</div>
    """, "rd")


def render_download(profiles: dict):
    st.markdown('<div style="margin-top:8px">', unsafe_allow_html=True)
    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None

    if st.session_state.pdf_bytes is None:
        if st.button("↓  GENERATE FULL INTELLIGENCE REPORT (PDF)", use_container_width=True):
            with st.spinner("Compiling dossier..."):
                st.session_state.pdf_bytes = get_pdf_bytes(profiles)
            st.rerun()
    else:
        st.download_button(
            label="↓  DOWNLOAD INTELLIGENCE REPORT (PDF)",
            data=st.session_state.pdf_bytes,
            file_name="exposed_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── main app ──────────────────────────────────────────────────────────────────

def build_profiles_from_signals(spotify_signals, chatgpt_signals) -> dict:
    """Calls the profile engine (Gemini) on whichever signals are available."""
    from profile_engine.generate_profile import (
        build_spotify_prompt, build_chatgpt_prompt, build_contrast_prompt, call_gpt
    )
    import datetime as _dt

    profiles = {"generated_at": _dt.datetime.utcnow().isoformat()}

    if spotify_signals:
        profiles["spotify"] = {
            "signals": spotify_signals,
            "profile": call_gpt(build_spotify_prompt(spotify_signals), "Spotify profile"),
        }

    if chatgpt_signals:
        profiles["chatgpt"] = {
            "signals": chatgpt_signals,
            "profile": call_gpt(build_chatgpt_prompt(chatgpt_signals), "ChatGPT profile"),
        }

    if spotify_signals and chatgpt_signals:
        profiles["contrast"] = call_gpt(
            build_contrast_prompt(spotify_signals, chatgpt_signals), "Contrast layer"
        )

    return profiles


def multi_upload_screen():
    st.markdown('<div class="card" style="text-align:center;padding:40px">', unsafe_allow_html=True)
    st.markdown('<div class="sec-tag muted" style="text-align:center">EXPOSED · Intelligence System</div>', unsafe_allow_html=True)
    st.markdown('<div class="headline" style="text-align:center">Drop your data export <span class="cy">.zip</span> files below</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted" style="font-size:13px;text-align:center;margin-bottom:24px">Upload Spotify and/or ChatGPT export zips — platform is detected automatically. Add as many as you like, then press Start.</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload data export zip files", type="zip", accept_multiple_files=True, label_visibility="collapsed"
    )

    start_clicked = False
    if uploaded_files:
        st.markdown(
            f'<div class="muted" style="font-size:12px;margin-top:16px;text-align:center">'
            f'{len(uploaded_files)} file(s) ready: {", ".join(f.name for f in uploaded_files)}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="margin-top:16px">', unsafe_allow_html=True)
        start_clicked = st.button(
            "▶  START ANALYSIS", use_container_width=True, type="primary"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return uploaded_files, start_clicked


def main():
    # dev shortcut — auto-load profiles.json from disk if present.
    # Visible on purpose: a silent version of this caused real confusion
    # during testing (same stale broken output kept showing after code
    # fixes, because this path bypassed the fix entirely).
    profiles = load_profiles("profiles.json")
    if profiles is not None:
        st.warning(
            "⚠ Loaded cached `profiles.json` from disk instead of running a "
            "fresh analysis. Delete that file from the project folder and "
            "reload if you want to upload new data or pick up code changes."
        )

    if profiles is None:
        if "profiles" not in st.session_state:
            st.session_state.profiles = None

        if st.session_state.profiles is None:
            uploaded_files, start_clicked = multi_upload_screen()

            if start_clicked and uploaded_files:
                from ingestion import ingest_uploads

                with st.spinner("Unzipping and detecting platforms..."):
                    result = ingest_uploads(uploaded_files)

                for w in result.warnings:
                    st.warning(w)
                for e in result.errors:
                    st.error(e)

                if not result.platforms_found:
                    st.error("No supported platform data found in the uploaded file(s).")
                    st.stop()

                st.success(f"Detected: {', '.join(p.capitalize() for p in result.platforms_found)}")

                with st.spinner("Generating psychological profile via Gemini..."):
                    st.session_state.profiles = build_profiles_from_signals(
                        result.spotify_signals, result.chatgpt_signals
                    )
                st.rerun()
            else:
                st.stop()

        profiles = st.session_state.profiles

    render_header(profiles)
    if "spotify" in profiles:
        render_spotify(profiles)
    if "chatgpt" in profiles:
        render_chatgpt(profiles)
    render_evidence(profiles)
    render_gap(profiles)
    render_download(profiles)


if __name__ == "__main__":
    main()
