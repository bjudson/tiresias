import json
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CONVENTIONS_PATH = Path(__file__).parent.parent / "CONVENTIONS.md"

EXTRACTION_PROMPT = """\
You are analyzing a dream using the approach of James
Hillman's imaginal psychology.

Extract 3–8 significant symbolic images from the dream text.

Look for:
- Figures: persons, animals, strangers, mythological or uncanny beings
- Weighted objects: things that carry unusual attention or strangeness
- Places, landscapes, thresholds, architectural features
- Actions that feel charged, repeated, or unresolved
- Qualities of light, color, atmosphere, or sound that stand out in the telling

Do not interpret. Do not assign universal meanings. Do not reduce images to
Jungian archetypes. Focus on what is IMAGE-FULL — what Hillman calls "the
image speaking for itself."

For each image, determine whether it matches an existing symbol or is
genuinely new. Match to an existing symbol if this dream's image is the same
core figure or place, even if it appears differently in this telling.

Existing symbols:
{existing_lines}

Return JSON only — no prose, no markdown fences:
{{
  "matched": ["slug1", "slug2"],
  "new": [
    {{
      "slug": "the-red-door",
      "title": "The Red Door",
      "summary": "a brief phrase naming this image as it recurs across dreams"
    }}
  ]
}}

Slugs are lowercase and hyphen-separated. Titles are concrete and specific —
not abstract categories.

Dream text:
{dream_text}"""


def _conventions() -> str:
    return CONVENTIONS_PATH.read_text()


AUDIT_PROMPT = """\
You are auditing a dream for missed symbol connections.

The dream currently has these symbols tagged: {already_tagged}

Review the dream text against the full symbol inventory below. Identify any \
symbols from the inventory that are clearly present in the dream but were not tagged.

Only flag genuine connections — where the dream's imagery substantially overlaps \
with the symbol's core image. Do not force weak or metaphorical connections. Do not \
re-suggest symbols that are already tagged.

Symbol inventory:
{symbol_lines}

Return JSON only — no prose, no markdown fences:
{{"missing": ["slug1", "slug2"]}}

If no symbols are missing, return {{"missing": []}}

Dream text:
{dream_text}"""


def audit_symbols(dream_text: str, already_tagged: list[str], all_symbols: list[dict]) -> list[str]:
    """Return slugs from all_symbols that are present in the dream but not in already_tagged."""
    client = anthropic.Anthropic()

    symbol_lines = "\n".join(
        f"- {s['slug']}: {s['title']} — {s['summary']}"
        for s in all_symbols
    ) or "(none)"

    tagged_str = ", ".join(already_tagged) if already_tagged else "(none)"

    prompt = AUDIT_PROMPT.format(
        already_tagged=tagged_str,
        symbol_lines=symbol_lines,
        dream_text=dream_text,
    )

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        system=_conventions(),
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(message.content[0].text).get("missing", [])


def extract_symbols(dream_text: str, existing_symbols: list[dict]) -> dict:
    """
    Call Claude to extract symbols from a dream.

    Returns {"matched": [slug, ...], "new": [{slug, title, summary}, ...]}
    """
    client = anthropic.Anthropic()

    existing_lines = "\n".join(
        f"- {s['slug']}: {s['title']} — {s['summary']}"
        for s in existing_symbols
    ) or "(none yet)"

    prompt = EXTRACTION_PROMPT.format(
        existing_lines=existing_lines,
        dream_text=dream_text,
    )

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=_conventions(),
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(message.content[0].text)
