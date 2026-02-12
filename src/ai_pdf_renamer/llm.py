from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

from .text_utils import chunk_text

logger = logging.getLogger(__name__)


def _sanitize_json_string_value(response: str, *, key: str) -> str:
    """
    Attempts to escape unescaped quotes inside a JSON string value for `key`.
    This is a best-effort fix for common LLM formatting issues.
    """
    import re

    # Fast-path regex replacement for common cases where the JSON is almost valid.
    pattern = r'("' + re.escape(key) + r'":\s*")(.*?)(")'

    def replacer(match: re.Match[str]) -> str:
        prefix, value, suffix = match.groups()
        fixed_value = re.sub(r'(?<!\\)"', r'\\"', value)
        return prefix + fixed_value + suffix

    sanitized = re.sub(pattern, replacer, response, flags=re.DOTALL)

    # If the string is still malformed because unescaped quotes prematurely closed the
    # value, try a best-effort salvage assuming a single-key JSON object.
    #
    # This is intentionally conservative and only aims to support the script's
    # prompts, which ask for JSON objects with a single string field.
    key_idx = sanitized.find(f'"{key}"')
    if key_idx == -1:
        return sanitized

    colon_idx = sanitized.find(":", key_idx)
    if colon_idx == -1:
        return sanitized

    first_quote = sanitized.find('"', colon_idx)
    if first_quote == -1:
        return sanitized

    close_brace = sanitized.rfind("}")
    if close_brace == -1:
        return sanitized

    # Find closing quote: the last unescaped " before } (respects \" in value).
    i = first_quote + 1
    last_quote = -1
    while i < close_brace and i < len(sanitized):
        if sanitized[i] == "\\" and i + 1 < len(sanitized):
            i += 2
            continue
        if sanitized[i] == '"':
            last_quote = i
        i += 1
    if last_quote <= first_quote:
        return sanitized

    raw_value = sanitized[first_quote + 1 : last_quote]
    # Escape only unescaped quotes so existing \" is preserved.
    fixed_value = re.sub(r'(?<!\\)"', r'\\"', raw_value)
    return sanitized[: first_quote + 1] + fixed_value + sanitized[last_quote:]


def parse_json_field(response: str, *, key: str) -> str | list[str] | None:
    resp_str = response.strip()
    if not resp_str.startswith("{"):
        return None

    try:
        data = json.loads(resp_str)
    except json.JSONDecodeError:
        try:
            data = json.loads(_sanitize_json_string_value(resp_str, key=key))
        except json.JSONDecodeError:
            return None

    value = data.get(key)
    if isinstance(value, list):
        if all(isinstance(x, str) for x in value):
            cleaned = [x.strip() for x in value if x and x.strip()]
            return cleaned or None
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lower() == "na":
            return None
        return stripped
    return None


@dataclass(frozen=True)
class LocalLLMClient:
    base_url: str = "http://127.0.0.1:11434/v1/completions"
    model: str = "llama3.2"
    timeout_s: float = 30.0

    def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        payload = {"model": self.model, "prompt": prompt, "temperature": temperature}
        try:
            resp = requests.post(self.base_url, json=payload, timeout=self.timeout_s)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return (
                data.get("choices", [{}])[0].get("text", "")
                if isinstance(data, dict)
                else ""
            ).strip()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.error("Error obtaining completion: %s", exc)
            return ""


def complete_json_with_retry(
    client: LocalLLMClient,
    prompt: str,
    *,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> str:
    temp = temperature
    last = ""
    for i in range(max_retries):
        last = client.complete(prompt, temperature=temp)
        if last.strip().startswith("{"):
            try:
                json.loads(last)
                return last
            except json.JSONDecodeError:
                pass
        temp += 0.2
        logger.info("Retry %s: New temperature=%s", i + 1, temp)
    return last


def _try_prompts_for_key(
    client: LocalLLMClient,
    prompts: list[str],
    *,
    key: str,
    temperature: float,
) -> str | list[str] | None:
    for i, prompt in enumerate(prompts):
        r = complete_json_with_retry(client, prompt, temperature=temperature + i * 0.2)
        v = parse_json_field(r, key=key)
        if v is not None:
            return v
    return None


def get_document_summary(
    client: LocalLLMClient,
    pdf_content: str,
    *,
    language: str = "de",
    temperature: float = 0.0,
    max_chars_single: int = 15000,
) -> str:
    text = pdf_content.strip()
    if len(text) < 50:
        return "na"

    if len(text) < max_chars_single:
        if language == "de":
            prompts = [
                (
                    "Fasse den folgenden Text in 1–2 präzisen Sätzen zusammen. "
                    'Nur reines JSON: {"summary":"..."}\n\n' + text
                ),
                (
                    "Erstelle bitte eine 1–2 Sätze Zusammenfassung als JSON "
                    '{"summary":"..."}, ohne weitere Erklärungen.\n\n' + text
                ),
                (
                    "Text:\n" + text + '\n\nGib jetzt nur {"summary":"..."} zurück. '
                    "Keine Entschuldigungen, keine Erklärungen!"
                ),
                (
                    'Achtung! Ich brauche reines JSON in der Form {"summary":"..."}. '
                    "Hier der Text:\n\n" + text
                ),
            ]
        else:
            prompts = [
                (
                    "Summarize the following text in 1–2 concise sentences. "
                    'Return ONLY JSON: {"summary":"..."}\n\n' + text
                ),
            ]
        val = _try_prompts_for_key(
            client,
            prompts,
            key="summary",
            temperature=temperature,
        )
        return val if isinstance(val, str) else "na"

    # Chunking for very large PDFs.
    chunks = chunk_text(text, chunk_size=8000, overlap=1000)
    partial: list[str] = []
    for chunk in chunks:
        if language == "de":
            chunk_prompt = (
                "Fasse den folgenden Text in 1–2 kurzen Sätzen zusammen. "
                'NUR reines JSON {"summary":"..."}, keine Erklärungen.\n\n' + chunk
            )
        else:
            chunk_prompt = (
                "Summarize the following text in 1–2 short sentences. "
                'Return ONLY {"summary":"..."} in JSON, no explanations.\n\n' + chunk
            )
        r = complete_json_with_retry(
            client, chunk_prompt, temperature=temperature, max_retries=3
        )
        v = parse_json_field(r, key="summary")
        partial.append(v if isinstance(v, str) else "")

    combined = " ".join(p for p in partial if p)
    if not combined:
        return "na"

    if language == "de":
        final_prompt = (
            "Hier mehrere Teilzusammenfassungen eines langen Dokuments:\n"
            + combined
            + "\n\nFasse sie in 1–2 prägnanten Sätzen zusammen. "
            'Nur reines JSON {"summary":"..."}.\n'
        )
    else:
        final_prompt = (
            "Here are multiple partial summaries of a large document:\n"
            + combined
            + "\n\nCombine them into 1–2 concise sentences. "
            'Return ONLY {"summary":"..."} in JSON.\n'
        )

    r_final = complete_json_with_retry(
        client,
        final_prompt,
        temperature=temperature + 0.2,
        max_retries=3,
    )
    v_final = parse_json_field(r_final, key="summary")
    return v_final if isinstance(v_final, str) else "na"


def get_document_keywords(
    client: LocalLLMClient,
    summary: str,
    *,
    language: str = "de",
    temperature: float = 0.0,
) -> list[str] | None:
    if language == "de":
        prompts = [
            (
                "Extrahiere bitte 5–7 Schlüsselwörter aus dieser Zusammenfassung.\n"
                "Gib ausschließlich eine Ausgabe in der Form:\n"
                '{"keywords":["KW1","KW2","KW3"]}\n\n'
                "Jetzt bitte NUR reines JSON, sonst nichts.\n"
                "Zusammenfassung:\n" + summary
            ),
            (
                "Bitte NUR reines JSON in der Form:\n"
                '{"keywords":["KW1","KW2"]}\n\n'
                "Hier die Zusammenfassung:\n" + summary
            ),
        ]
    else:
        prompts = [
            (
                "Extract 5–7 keywords from this summary. Return ONLY JSON:\n"
                '{"keywords":["KW1","KW2"]}\n\n'
                "Summary:\n" + summary
            )
        ]

    val = _try_prompts_for_key(client, prompts, key="keywords", temperature=temperature)
    return val if isinstance(val, list) else None


def get_document_category(
    client: LocalLLMClient,
    *,
    summary: str,
    keywords: list[str],
    language: str = "de",
    temperature: float = 0.0,
) -> str:
    keywords_joined = ", ".join(keywords)
    if language == "de":
        base_text = f"Zusammenfassung:\n{summary}\nKeywords:{keywords_joined}"
        prompts = [
            (
                "Bestimme eine sinnvolle Kategorie als reines JSON.\n"
                'Gib nur: {"category":"..."}\n\n'
                "Keine weiteren Erklärungen, nur JSON. Text:\n" + base_text
            ),
            ('Bitte nur {"category":"..."} - ohne Zusätze:\n' + base_text),
        ]
    else:
        base_text = f"Summary:\n{summary}\nKeywords:{keywords_joined}"
        prompts = [
            (
                "Determine a suitable category. Return ONLY JSON: "
                '{"category":"..."}\n\nText:\n' + base_text
            )
        ]

    val = _try_prompts_for_key(client, prompts, key="category", temperature=temperature)
    return val if isinstance(val, str) else "na"


def get_final_summary_tokens(
    client: LocalLLMClient,
    *,
    summary: str,
    keywords: list[str],
    category: str,
    language: str = "de",
    temperature: float = 0.0,
) -> list[str] | None:
    kw_str = ", ".join(keywords)
    base_text = (
        f"Zusammenfassung: {summary}\nSchlagworte: {kw_str}\nKategorie: {category}"
    )

    if language == "de":
        prompts = [
            (
                "Erstelle bitte bis zu 5 Stichworte (kurz! 1–2 Wörter pro Stichwort) "
                "als reines JSON.\n"
                '{"final_summary":"stichwort1,stichwort2"}\n\n'
                "WICHTIG: Keine Sätze, nur Stichworte. Nur JSON.\n\n" + base_text
            ),
            (
                'Bitte nur reines JSON {"final_summary":"stichwort1,stichwort2"}. '
                "Max. 5 Stichworte, keine Sätze!\n\n" + base_text
            ),
        ]
    else:
        prompts = [
            (
                "Return up to 5 short keywords (1–2 words each) as JSON:\n"
                '{"final_summary":"kw1,kw2"}\n\n'
                "Only JSON.\n\n" + base_text
            )
        ]

    val = _try_prompts_for_key(
        client, prompts, key="final_summary", temperature=temperature
    )
    if not isinstance(val, str):
        return None

    tokens = [t.strip() for t in val.split(",") if t.strip()]
    return tokens[:5] if tokens else None
