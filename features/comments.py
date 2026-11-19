"""F2 - Real-time comments feed and Offline Q&A history (Firebase-backed)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from services.firebase_manager import get_pool_manager

LIVE_FEED_SIZE = 30
MAX_COMMENT_LEN = 500


def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M") if ts else ""


def _comment_form() -> None:
    with st.form("comment_form", clear_on_submit=True):
        text = st.text_area("Your question or suggestion", max_chars=MAX_COMMENT_LEN, height=90)
        name = st.text_input("Name (optional - leave empty to stay anonymous)", max_chars=40)
        if st.form_submit_button("Send", type="primary", use_container_width=True):
            if text.strip():
                get_pool_manager().add_comment(text, name or "Anonymous")
                st.toast("Sent!")
            else:
                st.warning("Write something first.")


@st.fragment(run_every=3)
def _live_feed() -> None:
    comments = get_pool_manager().get_comments(limit=LIVE_FEED_SIZE)
    st.caption(f"Live · auto-refreshing every 3 s · {datetime.now():%H:%M:%S}")
    if not comments:
        st.info("No comments yet.")
        return
    for c in reversed(comments):
        with st.container(border=True):
            st.markdown(f"**{c.get('author', 'Anonymous')}** · {_fmt(c.get('ts', 0))}")
            st.write(c.get("text", ""))


def _offline_history(role: str) -> None:
    comments = get_pool_manager().get_comments()
    if not comments:
        st.info("No comments have been saved yet.")
        return

    df = pd.DataFrame(comments)
    df["time"] = df["ts"].apply(lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"))
    df = df[["time", "author", "text"]]

    query = st.text_input("🔎 Search", placeholder="keyword...")
    newest_first = st.toggle("Newest first", value=True)
    if query:
        df = df[df["text"].str.contains(query, case=False, na=False, regex=False)]
    if newest_first:
        df = df.iloc[::-1]

    st.caption(f"{len(df)} comment(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download Q&A (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"qa_history_{datetime.now():%Y%m%d}.csv",
        mime="text/csv",
    )

    if role == "Lecturer":
        with st.expander("Danger zone"):
            confirm = st.checkbox("I understand this deletes all comments")
            if st.button("Delete all comments", disabled=not confirm):
                get_pool_manager().clear_comments()
                st.rerun()


def render(role: str) -> None:
    st.header("💬 Comments & Q&A")
    live_tab, offline_tab = st.tabs(["Live", "Offline Q&A"])
    with live_tab:
        _comment_form()
        _live_feed()
    with offline_tab:
        _offline_history(role)
