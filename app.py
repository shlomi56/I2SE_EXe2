"""ClassMate - KISS web-based teaching tool (Ex2).

Run with:  streamlit run app.py
"""
from __future__ import annotations

import hmac
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="ClassMate", page_icon="🎓", layout="centered", initial_sidebar_state="auto")

from features import attendance, comments, hw_review, polls, video_summary  # noqa: E402
from services.firebase_manager import firebase_is_configured  # noqa: E402
from services.gemini_service import gemini_is_configured  # noqa: E402

# label -> (module, needs_firebase, needs_gemini)
PAGES = {
    "📸 Attendance": (attendance, False, False),
    "💬 Comments": (comments, True, False),
    "📊 Polls": (polls, True, False),
    "🎬 Video Summary": (video_summary, False, True),
    "🧑‍💻 HW Review": (hw_review, True, True),
}
ROLE_PAGES = {
    "Lecturer": list(PAGES),
    "Student": ["💬 Comments", "📊 Polls", "🧑‍💻 HW Review"],
}


def _check_pin(pin: str) -> bool:
    expected = os.getenv("LECTURER_PIN", "")
    return bool(expected) and hmac.compare_digest(pin.encode(), expected.encode())


def sidebar_role() -> str:
    st.sidebar.title("🎓 ClassMate")
    st.session_state.setdefault("lecturer_unlocked", False)

    role = st.sidebar.radio("I am a...", ["Student", "Lecturer"], horizontal=True)
    if role == "Lecturer" and not st.session_state.lecturer_unlocked:
        if not os.getenv("LECTURER_PIN"):
            st.sidebar.error("LECTURER_PIN is not set in .env")
            return "Student"
        with st.sidebar.form("pin_form"):
            pin = st.text_input("Lecturer PIN", type="password")
            if st.form_submit_button("Unlock"):
                if _check_pin(pin):
                    st.session_state.lecturer_unlocked = True
                    st.rerun()
                else:
                    st.error("Wrong PIN")
        return "Student"

    if role == "Lecturer" and st.sidebar.button("🔒 Lock lecturer mode"):
        st.session_state.lecturer_unlocked = False
        st.rerun()
    return role


def main() -> None:
    role = sidebar_role()
    page = st.sidebar.radio("Go to", ROLE_PAGES[role])
    st.sidebar.caption(f"Signed in as **{role}**")

    module, needs_firebase, needs_gemini = PAGES[page]
    missing = []
    if needs_firebase and not firebase_is_configured():
        missing.append("Firebase (FIREBASE_DATABASE_URL + FIREBASE_CREDENTIALS_PATH/JSON)")
    if needs_gemini and not gemini_is_configured():
        missing.append("Gemini (GEMINI_API_KEY)")
    if missing:
        st.error("This page needs configuration in `.env`: " + "; ".join(missing))
        st.caption("Copy `.env.example` to `.env`, fill in the values, then restart the app.")
        return

    try:
        module.render(role)
    except Exception as exc:  # keep the demo alive on network/config errors
        st.error(f"Something went wrong: {exc}")


main()
