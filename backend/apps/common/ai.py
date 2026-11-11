"""
Dual-path AI layer: a real OpenAI chat-completion call when
`OPENAI_API_KEY` is set, otherwise a fully offline, deterministic stub. This
lets the whole summarize-meeting pipeline (model, serializer, view, seed
data, tests) be built, run, and tested with zero network access and zero
cost.

There is no embeddings model and no vector database anywhere in this app -
`summarize_meeting_notes` is the single AI touchpoint, a plain chat-completion
call that turns freeform meeting notes into a short summary plus a list of
action items.

*** IMPORTANT ***: the stub summary/action-items are NOT a real summary of
the notes - they are a reproducible, deterministic transformation (seeded by
a hash of the input text) so the same `raw_notes` always produces the same
stub output. This determinism is what the test suite relies on. Real
summarization quality - actually understanding the notes - requires a real
`OPENAI_API_KEY` so `summarize_meeting_notes` calls the real chat
completions API.
"""
import hashlib
import json
import re

from django.conf import settings

_ACTION_VERBS = [
    "Follow up on",
    "Schedule a review of",
    "Confirm next steps for",
    "Draft a summary document for",
    "Share updates with the team about",
    "Circle back with stakeholders on",
]

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_SPLIT_RE = re.compile(r"[.!?\n]+")


def is_stub_mode() -> bool:
    return not bool(settings.OPENAI_API_KEY)


def summarize_meeting_notes(raw_notes: str) -> dict:
    """Return {"summary": str, "action_items": list[str]} for `raw_notes`.

    Real path (OPENAI_API_KEY set): calls the OpenAI chat completions API,
    asking for structured JSON. The response is parsed defensively - if the
    model doesn't return valid JSON with the expected shape, we fall back to
    a minimal, clearly-labelled result instead of raising.

    Stub path (no key): deterministic, offline. The summary is the first one
    or two sentences of the notes; the action items are synthesized from a
    sha256 hash of the text, so the SAME raw_notes always produces the SAME
    stub output across calls and across processes.
    """
    raw_notes = (raw_notes or "").strip()

    if settings.OPENAI_API_KEY:
        return _summarize_with_openai(raw_notes)
    return _summarize_stub(raw_notes)


def _summarize_with_openai(raw_notes: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize meeting notes for a team. Given freeform "
                    "meeting notes, return a JSON object with exactly two "
                    'keys: "summary" (a concise paragraph, 2-4 sentences) '
                    'and "action_items" (a JSON array of short, concrete '
                    "action item strings, each one task). Return JSON only, "
                    "no surrounding prose."
                ),
            },
            {"role": "user", "content": raw_notes},
        ],
    )
    content = response.choices[0].message.content or ""
    return _parse_ai_response(content, raw_notes)


def _parse_ai_response(content: str, raw_notes: str) -> dict:
    """Defensively parse the model's JSON response. Never raises - falls
    back to a minimal, clearly-labelled result if the content isn't valid
    JSON or doesn't have the expected shape."""
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        data = json.loads(match.group(0) if match else content)
        summary = data.get("summary")
        action_items = data.get("action_items")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("missing/empty summary")
        if not isinstance(action_items, list):
            action_items = []
        action_items = [str(item).strip() for item in action_items if str(item).strip()]
        return {"summary": summary.strip(), "action_items": action_items}
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        fallback_summary = content.strip() or f"[AI summary unavailable] {raw_notes[:200]}"
        return {"summary": fallback_summary, "action_items": []}


def _summarize_stub(raw_notes: str) -> dict:
    if not raw_notes:
        return {
            "summary": "[STUB SUMMARY — set OPENAI_API_KEY for real output] No notes were provided.",
            "action_items": [],
        }

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(raw_notes) if s.strip()]
    summary_source = " ".join(sentences[:2]) if sentences else raw_notes[:240]
    summary = f"[STUB SUMMARY — set OPENAI_API_KEY for real output] {summary_source}"

    digest = hashlib.sha256(raw_notes.encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)

    clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(raw_notes) if c.strip()]
    num_items = 2 + (seed % 3)  # deterministic count in [2, 4]

    action_items = []
    for i in range(num_items):
        verb = _ACTION_VERBS[(seed + i) % len(_ACTION_VERBS)]
        if clauses:
            topic = clauses[(seed + i) % len(clauses)]
            topic = topic[:80].strip().rstrip(".,;:")
            if len(topic) > 4:
                topic = topic[0].lower() + topic[1:]
        else:
            topic = "the discussion above"
        action_items.append(f"{verb} {topic}")

    return {"summary": summary, "action_items": action_items}
