"""F5 - Deep LLM homework review using an anonymous Firebase Cloud Pool for peer context.

Flow (SRS REQ-5.1..5.4): paste/upload code -> push to /submissions -> fetch a prior
anonymous peer submission -> Gemini comparative review."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from services.firebase_manager import get_pool_manager
from services.gemini_service import get_gemini_service

MAX_CODE_CHARS = 20_000
LANGUAGES = {
    "Python": "py",
    "Java": "java",
    "C": "c",
    "C++": "cpp",
    "C#": "cs",
    "JavaScript": "js",
    "TypeScript": "ts",
    "Other": "txt",
}
HIGHLIGHT = {
    "Python": "python", "Java": "java", "C": "c", "C++": "cpp", "C#": "csharp",
    "JavaScript": "javascript", "TypeScript": "typescript", "Other": "text",
}
UPLOAD_TYPES =sorted(set(LANGUAGES.values()) | {"h", "hpp", "txt"})
EXT_TO_LANGUAGE = {ext: lang for lang, ext in LANGUAGES.items()}


def _load_uploaded_file() -> None:
    """Copy an uploaded source file into the text area (once per new file)."""
    uploaded = st.session_state.get("hw_upload")
    if uploaded is None:
        return
    try:
        st.session_state.hw_code = uploaded.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        st.session_state.hw_code = uploaded.getvalue().decode("latin-1")
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    if ext in ("h", "hpp"):
        ext = "cpp"
    st.session_state.hw_language = EXT_TO_LANGUAGE.get(ext, st.session_state.get("hw_language", "Python"))


def render(role: str) -> None:
    st.header("🧑‍💻 Homework Review")
    st.write(
        "Paste or upload your code. It is stored **anonymously** in the class Cloud Pool, "
        "and the AI compares it with another anonymous submission."
    )
    st.session_state.setdefault("hw_code", "")
    st.session_state.setdefault("hw_language", "Python")

    st.file_uploader("Upload a source file (optional)", type=UPLOAD_TYPES, key="hw_upload", on_change=_load_uploaded_file)
    language = st.selectbox("Language", list(LANGUAGES), key="hw_language")
    code = st.text_area("Your code", key="hw_code", height=300, placeholder="Paste your code here...")

    if len(code) > MAX_CODE_CHARS:
        st.warning(f"Code is {len(code):,} characters; the limit is {MAX_CODE_CHARS:,}.")

    submit = st.button(
        "🔍 Submit for review", type="primary", use_container_width=True,
        disabled=not code.strip() or len(code) > MAX_CODE_CHARS,
    )
    if submit:
        try:
            pool = get_pool_manager()
            with st.status("Reviewing your submission...", expanded=True) as status:
                st.write("Saving anonymously to the Cloud Pool...")
                own_key = pool.push_submission(code, language)
                st.write("Fetching an anonymous peer submission...")
                peer = pool.get_peer_submission(exclude_key=own_key, language=language)
                st.write("Asking Gemini for a comparative review...")
                review = get_gemini_service().compare_homework(code, peer["code"] if peer else None, language)
                status.update(label="Review ready!", state="complete", expanded=False)
            st.session_state.hw_review = {"review": review, "peer": peer, "language": language}
        except Exception as exc:
            st.error(f"Review failed: {exc}")

    result = st.session_state.get("hw_review")
    if result:
        st.divider()
        st.markdown(result["review"])
        peer = result["peer"]
        if peer:
            with st.expander("Anonymous peer submission used for comparison"):
                st.code(peer["code"], language=HIGHLIGHT.get(peer.get("language", ""), "text"))
        else:
            st.info("You're the first submission in the pool — future reviews will compare against yours.")
        st.download_button(
            "⬇️ Download review (.md)",
            data=result["review"].encode("utf-8"),
            file_name=f"hw_review_{datetime.now():%Y%m%d_%H%M}.md",
            mime="text/markdown",
        )
