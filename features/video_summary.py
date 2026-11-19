"""F4 - ML lecture summary: upload class video/audio, Gemini returns a Markdown summary."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime

import streamlit as st

from services.gemini_service import get_gemini_service

MIME_TYPES = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
}


def render(role: str) -> None:
    st.header("🎬 Lecture Summary")
    if role != "Lecturer":
        st.info("Lecture summaries are available to the lecturer only.")
        return

    st.write("Upload a recording from Zoom, Meet or Classroom. Gemini listens to it directly — no separate transcription.")
    media = st.file_uploader("Recording", type=list(MIME_TYPES))
    if media is None:
        return

    ext = media.name.rsplit(".", 1)[-1].lower()
    if ext in ("mp4", "mov", "webm"):
        st.video(media)
    else:
        st.audio(media)

    if st.button("✨ Generate summary", type="primary", use_container_width=True):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                tmp.write(media.getbuffer())
                tmp_path = tmp.name
            with st.spinner("Uploading to Gemini and summarizing (up to ~2 min)..."):
                st.session_state.summary_md = get_gemini_service().summarize_media(tmp_path, MIME_TYPES[ext])
                st.session_state.summary_source = media.name
        except Exception as exc:
            st.error(f"Summary failed: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    summary = st.session_state.get("summary_md")
    if summary:
        st.divider()
        st.caption(f"Summary of {st.session_state.get('summary_source', 'recording')}")
        st.markdown(summary)
        st.download_button(
            "⬇️ Download summary (.md)",
            data=summary.encode("utf-8"),
            file_name=f"lecture_summary_{datetime.now():%Y%m%d}.md",
            mime="text/markdown",
        )
