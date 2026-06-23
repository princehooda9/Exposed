# EXPOSED — Intelligence System

Upload your Spotify and ChatGPT data export .zip files directly.
The app auto-detects which platform each file belongs to, unzips,
parses, and generates a psychological profile — proven with your own data.

---

## Project structure

```
EXPOSED/
├── parsers/
│   ├── spotify_parser.py          ← extracts Spotify 
│   └── chatgpt_parser.py          ← extracts ChatGPT 
├── profile_engine/
│   └── generate_profile.py        ← calls Gemini
├── ingestion.py                   ← auto-detects platform from uploaded zips
├── dashboard.py                   ← Streamlit app (upload + UI + everything)
├── pdf_report.py                  ← generates the downloadable PDF dossier
├── requirements.txt read the file requirements before installing 
└── sample_output/                 ← example output
    └── exposed_report.pdf
```
Youtube video link: https://youtu.be/0--Zddtdflk
---

## Setup

```bash
pip install -r requirements.txt
```

Open the `.env` file in the project root and paste your Gemini API key:

```
GEMINI_API_KEY=your_actual_key_here
EXPOSED_MODEL=gemini-2.5-flash
```

That's it — no need to manually set environment variables in your terminal,
the app reads `.env` automatically every time it runs.

Get a free Gemini API key at: https://aistudio.google.com/apikey
(no credit card required)

---

## Run it

```bash
streamlit run dashboard.py
```

Then in the browser:

1. **Drag in your export .zip files** — Spotify's, ChatGPT's, or both at once.
   No need to unzip first, no need to specify which platform — it's detected
   automatically by inspecting filenames inside each zip.
2. The app unzips, parses, and calls Gemini to generate your profile.
3. Your full dossier renders — platform profiles, Evidence Explorer, and
   (if both platforms were uploaded) the Gap / contrast layer.
4. Click **Generate Full Intelligence Report (PDF)** to download the dossier.

You can upload just one platform — the dashboard adapts and skips sections
that need both (like the Gap layer) until you have both.

---

## Getting your data

**Spotify:**
Account → Privacy Settings → Download your data → wait up to 5 days
→ you'll receive a `.zip`, upload it as-is.

**ChatGPT:**
Settings → Data Controls → Export data → wait up to 24 hours
→ you'll receive a `.zip`. Recent exports split conversations into
multiple files (`conversations-000.json`, `conversations-001.json`, ...)
instead of one `conversations.json` — both formats are auto-detected
and handled, upload the zip as-is either way.

---

## Notes

- All unzip + parsing happens locally in the Streamlit process. Only
  extracted behavioral signals (no raw conversation text or full song
  lists) are sent to the Gemini API.
- `sample_output/` shows what a finished run looks like.
- The video history files inside Spotify's export and the included
  ReadMe PDF are automatically ignored by the parser.

---

## Validated against real data (2026-06-21)

Full pipeline (ingestion → parsers → mock-profile shape → PDF render)
tested end-to-end against a real Spotify export (8,979 valid plays,
384.6 hrs) and a real ChatGPT export (500 conversations, 3,868 user
messages).



