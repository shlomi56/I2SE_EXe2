"""F3 - On-the-spot polls: lecturer creates, students vote, results update live."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pandas as pd
import streamlit as st

from services.firebase_manager import get_pool_manager

MIN_OPTIONS, MAX_OPTIONS = 2, 6


def _results_chart(poll: Dict[str, Any]) -> None:
    total = sum(poll["counts"])
    st.markdown(f"### {poll['question']}")
    st.caption(f"{total} vote(s) · updated {datetime.now():%H:%M:%S}")
    df = pd.DataFrame({"Option": poll["options"], "Votes": poll["counts"]}).set_index("Option")
    st.bar_chart(df, horizontal=True)


# ---------------------------------------------------------------- Lecturer
def _poll_creator() -> None:
    st.subheader("Create a poll")
    n_options = st.number_input("Number of options", MIN_OPTIONS, MAX_OPTIONS, 4, step=1)
    with st.form("poll_form", clear_on_submit=True):
        question = st.text_input("Question")
        options = [st.text_input(f"Option {i + 1}", key=f"opt_{i}") for i in range(int(n_options))]
        if st.form_submit_button("🚀 Publish poll", type="primary", use_container_width=True):
            options = [o.strip() for o in options if o.strip()]
            if not question.strip():
                st.warning("Enter a question.")
            elif len(options) < MIN_OPTIONS:
                st.warning(f"Enter at least {MIN_OPTIONS} options.")
            elif len(set(options)) != len(options):
                st.warning("Options must be unique.")
            else:
                get_pool_manager().create_poll(question, options)
                st.success("Poll is live!")


@st.fragment(run_every=2)
def _lecturer_live_results() -> None:
    poll = get_pool_manager().get_active_poll()
    if not poll:
        st.info("No active poll. Create one above.")
        return
    _results_chart(poll)
    if st.button("⏹ Close poll"):
        get_pool_manager().close_poll()
        st.rerun()


# ---------------------------------------------------------------- Student
@st.fragment(run_every=2)
def _student_view() -> None:
    poll = get_pool_manager().get_active_poll()
    if not poll:
        st.info("No active poll right now. This page refreshes automatically.")
        return

    voted = st.session_state.setdefault("voted_polls", set())
    if poll["id"] in voted:
        st.success("Thanks for voting!")
        _results_chart(poll)
        return

    st.markdown(f"### {poll['question']}")
    for idx, option in enumerate(poll["options"]):
        if st.button(option, key=f"vote_{poll['id']}_{idx}", use_container_width=True):
            get_pool_manager().vote(poll["id"], idx)
            voted.add(poll["id"])
            st.rerun(scope="fragment")


def render(role: str) -> None:
    st.header("📊 Polls")
    if role == "Lecturer":
        _poll_creator()
        st.divider()
        st.subheader("Live results")
        _lecturer_live_results()
    else:
        _student_view()
