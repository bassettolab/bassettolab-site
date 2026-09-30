#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
client = OpenAI()

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
}

FENCE_RE = re.compile(r"(^.{3}[^\n]*\n.*?^.{3}\s*$)", re.MULTILINE | re.DOTALL)
URL_RE = re.compile(r"https?://[^\s)>\"]+")
BACKTICK = chr(96)
INLINE_CODE_RE = re.compile(re.escape(BACKTICK) + r"[^\n" + re.escape(BACKTICK) + r"]+" + re.escape(BACKTICK))


def protect(text: str):
    protected = {}

    def stash(match, prefix):
        key = f"@@{prefix}_{len(protected)}@@"
        protected[key] = match.group(0)
        return key

    text = FENCE_RE.sub(lambda m: stash(m, "FENCE"), text)
    text = INLINE_CODE_RE.sub(lambda m: stash(m, "INLINE"), text)
    text = URL_RE.sub(lambda m: stash(m, "URL"), text)
    return text, protected


def restore(text: str, protected: dict):
    for key, value in protected.items():
        text = text.replace(key, value)
    for key in protected:
        if key in text:
            raise RuntimeError(f"Placeholder was not restored: {key}")
    return text


def target_path(source: Path, lang: str) -> Path:
    if source.name != "index.md":
        raise ValueError(f"Source must be index.md: {source}")
    return source.with_name(f"index.{lang}.md")


def translate(source_text: str, language: str) -> str:
    masked, protected = protect(source_text)

    instructions = f"""
Translate the Hugo Markdown article from Brazilian Portuguese into {language}.

Rules:
- Return only the complete translated Markdown file.
- Preserve the exact Markdown structure and section order.
- Preserve YAML front matter keys and formatting.
- Translate only human-readable prose, title, description, headings and image alt text.
- Keep these front matter values unchanged: date, tags, categories, toc, type, featured, draft.
- Keep Oracle product names, acronyms, field names, table names, XML tags, SQL identifiers, XSL names, CFOP values and technical identifiers unchanged.
- Never alter placeholders such as @@FENCE_0@@, @@INLINE_0@@ or @@URL_0@@.
- Do not add, remove, summarize, improve, or reinterpret content.
- English and Spanish versions must remain structurally equivalent to the Portuguese source.
""".strip()

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=masked,
    )

    result = response.output_text.strip()
    result = restore(result, protected)

    if not result.startswith("---"):
        raise RuntimeError("Translated file does not start with Hugo front matter.")

    return result.rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        print("No source files supplied.")
        return

    for raw in sys.argv[1:]:
        source = Path(raw)
        if not source.exists() or source.name != "index.md":
            print(f"Skipping {source}")
            continue

        source_text = source.read_text(encoding="utf-8")
        print(f"Translating {source}")

        for lang, language in LANGUAGES.items():
            output = target_path(source, lang)
            translated = translate(source_text, language)
            output.write_text(translated, encoding="utf-8")
            print(f"  -> {output}")


if __name__ == "__main__":
    main()
