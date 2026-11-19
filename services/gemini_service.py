"""Google Gemini integration: multimodal lecture summary (F4) and
comparative homework review (F5)."""
from __future__ import annotations

import os
import time
from typing import Optional

import streamlit as st
from google import genai
from google.genai import types

# Uses the current `google-genai` SDK (the legacy `google-generativeai` package is
# end-of-life). Override the model with GEMINI_MODEL in .env.
DEFAULT_MODEL = "gemini-2.5-flash"

SUMMARY_PROMPT = """You are a teaching assistant. Watch/listen to this recorded class session
and produce a concise, well-structured summary in Markdown with EXACTLY these sections:

## Core Concepts
Bullet list of the main topics and ideas taught, each with a one-sentence explanation.

## Q&A
Questions asked during the session (by students or the lecturer) and the answers given.
If no questions were asked, write "No questions were raised."

## Action Items
Homework, deadlines, readings or follow-ups mentioned. If none, write "None mentioned."

Write in the same language the lecturer speaks. Do not invent content that is not in the recording."""

REVIEW_PROMPT = """You are an experienced software engineering teaching assistant.
Review the student's {language} submission below{peer_clause}.

Respond in Markdown with these sections:

## Summary
What the code does, in 2-3 sentences.

## Correctness
Bugs, edge cases and logic errors (quote the relevant lines).

## Code Quality
Readability, naming, structure, OOP/design principles.

## Complexity
Time and space complexity of the main logic.

## Comparison with a Peer Approach
{comparison_instructions}

## Suggestions
A prioritized, numbered list of concrete improvements.

Be constructive and specific. Never reveal or guess the identity of any author.

### Student submission
```{language_tag}
{code}
```
{peer_block}"""

PEER_INSTRUCTIONS = (
    "Compare the student's approach with the anonymous peer submission: design choices, "
    "efficiency, readability, and what each could learn from the other. Use a short table if helpful."
)
NO_PEER_INSTRUCTIONS = (
    "No peer submission is available yet in the Cloud Pool. State this in one sentence and "
    "instead describe a common alternative approach to the same problem."
)


class GeminiConfigError(RuntimeError):
    """Raised when the Gemini API key is missing."""


def gemini_is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


class GeminiService:
    FILE_PROCESSING_TIMEOUT_S = 120
    POLL_INTERVAL_S = 2
    REQUEST_TIMEOUT_MS = 600_000  # long recordings can take a few minutes to summarize

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None:
        api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise GeminiConfigError("Set GEMINI_API_KEY in your .env file.")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=self.REQUEST_TIMEOUT_MS)
        )

    # ------------------------------------------------------------------ F4
    def summarize_media(self, file_path: str, mime_type: str) -> str:
        """Upload audio/video via the Gemini File API and return a Markdown summary."""
        uploaded = self._client.files.upload(
            file=file_path, config=types.UploadFileConfig(mime_type=mime_type)
        )
        try:
            deadline = time.time() + self.FILE_PROCESSING_TIMEOUT_S
            while uploaded.state == types.FileState.PROCESSING:
                if time.time() > deadline:
                    raise TimeoutError("Gemini is taking too long to process the file. Try a shorter clip.")
                time.sleep(self.POLL_INTERVAL_S)
                uploaded = self._client.files.get(name=uploaded.name)
            if uploaded.state != types.FileState.ACTIVE:
                state = uploaded.state.name if uploaded.state else "UNKNOWN"
                error = f": {uploaded.error.message}" if uploaded.error and uploaded.error.message else ""
                raise RuntimeError(f"Gemini could not process the file (state: {state}){error}")

            response = self._client.models.generate_content(
                model=self.model_name, contents=[uploaded, SUMMARY_PROMPT]
            )
            return self._text(response)
        finally:
            try:
                self._client.files.delete(name=uploaded.name)
            except Exception:  # cleanup is best-effort
                pass

    # ------------------------------------------------------------------ F5
    def compare_homework(self, code: str, peer_code: Optional[str], language: str) -> str:
        language_tag = language.lower().replace("+", "p").replace("#", "sharp")
        if peer_code:
            peer_clause = " and compare it with an anonymous peer submission for the same assignment"
            peer_block = f"\n### Anonymous peer submission\n```{language_tag}\n{peer_code}\n```\n"
            comparison = PEER_INSTRUCTIONS
        else:
            peer_clause, peer_block, comparison = "", "", NO_PEER_INSTRUCTIONS

        prompt = REVIEW_PROMPT.format(
            language=language,
            language_tag=language_tag,
            peer_clause=peer_clause,
            comparison_instructions=comparison,
            code=code,
            peer_block=peer_block,
        )
        response = self._client.models.generate_content(model=self.model_name, contents=prompt)
        return self._text(response)

    @staticmethod
    def _text(response: types.GenerateContentResponse) -> str:
        text = response.text  # None when the response was blocked or empty
        if not text or not text.strip():
            reason = ""
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = f" (blocked: {response.prompt_feedback.block_reason.name})"
            elif response.candidates and response.candidates[0].finish_reason:
                reason = f" (finish reason: {response.candidates[0].finish_reason.name})"
            raise RuntimeError(f"Gemini returned an empty response{reason}.")
        return text


@st.cache_resource(show_spinner=False)
def get_gemini_service() -> GeminiService:
    return GeminiService()
