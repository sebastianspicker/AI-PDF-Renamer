```python
import os
import re
import json
import requests
import logging
import tiktoken
import fitz  # PyMuPDF
from datetime import datetime

###############################################################################
# LOGGING CONFIGURATION
###############################################################################
logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("error.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

###############################################################################
# GLOBAL PARAMETERS
###############################################################################
max_length = 15000
max_content_length_for_api = 1000

###############################################################################
# DATE EXTRACTION
###############################################################################
def extract_date_from_content(content: str) -> str:
    """
    Searches the text for date formats (YYYY-MM-DD or DD.MM.YYYY)
    and returns 'YYYY-MM-DD'. If no date is found, returns today's date.
    """
    match = re.search(r'\b(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})\b', content)
    if match:
        year, month, day = match.groups()
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except Exception as e:
            logger.error(f"Error in extract_date_from_content (YYYY-MM-DD): {e}")

    match2 = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', content)
    if match2:
        day, month, year = match2.groups()
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except Exception as e:
            logger.error(f"Error in extract_date_from_content (DD.MM.YYYY): {e}")

    # Fallback: today's date (YYYY-MM-DD)
    return datetime.now().strftime("%Y-%m-%d")

###############################################################################
# HEURISTIC PATTERNS - loaded from external JSON
###############################################################################
# The "heuristic_patterns.json" file has the format:
# {
#   "patterns": [
#       ["(?i)\\bschulzeugnis\\b|...", "schulzeugnis"],
#       ...
#   ]
# }
with open("heuristic_patterns.json", "r", encoding="utf-8") as f:
    data = json.load(f)

HEURISTIC_PATTERNS = [(p[0], p[1]) for p in data["patterns"]]

with open("heuristic_scores.json", "r", encoding="utf-8") as f:
    data = json.load(f)

HEURISTIC_SCORES = []
for entry in data["patterns"]:
    pattern = entry["regex"]
    cat = entry["category"]
    sc = entry["score"]  # float value
    HEURISTIC_SCORES.append((pattern, cat, sc))
    
with open("meta_stopwords.json", "r", encoding="utf-8") as f:
    stopwords_data = json.load(f)
    
META_STOPWORDS = set(word.lower() for word in stopwords_data["stopwords"])

def get_heuristic_category(pdf_content: str) -> str:
    """
    Uses the loaded HEURISTIC_SCORES (pattern, category, score).
    For each match in the content, sums up the scores. 
    Returns the category with the highest total score or 'unknown' if nothing matched.
    """
    text_lower = pdf_content.lower()
    category_scores = {}

    for pattern, cat, score in HEURISTIC_SCORES:
        if re.search(pattern, text_lower):
            if cat not in category_scores:
                category_scores[cat] = 0
            category_scores[cat] += score

    if not category_scores:
        return 'unknown'

    # Determine the category with the highest score
    best_cat = max(category_scores, key=category_scores.get)
    best_score = category_scores[best_cat]
    logger.info(f"Heuristic scoring result: {category_scores}. Best: {best_cat} (Score={best_score})")
    return best_cat

def combine_categories(cat_ki: str, cat_heur: str) -> str:
    """
    If the heuristic category is not 'unknown', we prioritize the heuristic.
    Otherwise, we take the KI category. If there's a conflict, log it and use heuristic.
    """
    if cat_heur == 'unknown':
        return cat_ki
    if cat_ki in ['document', 'unknown', 'na', '']:
        return cat_heur
    if cat_ki != cat_heur:
        logger.info(f"Conflict: KI category={cat_ki}, Heuristic={cat_heur}. Prioritizing heuristic.")
        return cat_heur
    return cat_ki

###############################################################################
# PDF EXTRACTION
###############################################################################
def content_token_cut(content, num_tokens, max_len):
    """
    Iteratively shortens the text by 10% until the total token count 
    is <= max_len. This avoids overly large strings for the LLM.
    """
    while num_tokens > max_len:
        new_length = int(len(content) * 0.9)
        content = content[:new_length]
        num_tokens = len(tiktoken.get_encoding("cl100k_base").encode(content))
    return content

def pdfs_to_text_string(filepath) -> str:
    """
    Opens a PDF file with PyMuPDF (fitz), extracts text using 
    get_text("text"), get_text("blocks"), get_text("rawdict"), 
    and combines them into a single string.
    """
    try:
        doc = fitz.open(filepath)
    except Exception as e:
        logger.error(f"Error opening file {filepath}: {e}")
        return ""

    content = ""
    for page_number in range(doc.page_count):
        txt_text = ""
        txt_blocks = ""
        txt_raw = ""

        try:
            page = doc[page_number]
        except Exception as e:
            logger.error(f"Error accessing page {page_number} in {filepath}: {e}")
            continue

        # get_text("text")
        try:
            txt_text = page.get_text("text")
        except Exception:
            pass

        # get_text("blocks")
        try:
            blocks = page.get_text("blocks")
            txt_blocks = " ".join(block[4] for block in blocks if block[4].strip())
        except Exception:
            pass

        # get_text("rawdict")
        try:
            rawdict = page.get_text("rawdict")
            txt_raw = " ".join(
                " ".join(line.get("spans", [{}])[0].get("text", "")
                         for line in block.get("lines", []))
                for block in rawdict.get("blocks", [])
            )
        except Exception:
            pass

        combined_page_text = " ".join([txt_text, txt_blocks, txt_raw]).strip()
        if combined_page_text:
            content += combined_page_text + "\n"
            logger.info(f"Combined extracted {len(combined_page_text)} characters from page {page_number} of {filepath}")
        else:
            logger.info(f"Page {page_number} in {filepath} yields no text.")

    if not content.strip():
        content = "Content is empty or contains only whitespace."

    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(content))
    if num_tokens > max_length:
        content = content_token_cut(content, num_tokens, max_length)

    return content

###############################################################################
# KI HELPERS (get_field, get_field_with_retry, sanitize, parse_json_response)
###############################################################################
def get_field(prompt, temperature=0.0) -> str:
    """
    Sends a prompt to the local LLM endpoint and returns the resulting string or empty.
    Expects a running local service at http://127.0.0.1:11434/v1/completions.
    """
    try:
        payload = {"model": "llama3.2", "prompt": prompt, "temperature": temperature}
        resp = requests.post("http://127.0.0.1:11434/v1/completions", json=payload)
        return resp.json().get("choices", [{}])[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"Error obtaining field: {e}")
        return ""

def get_field_with_retry(prompt, initial_temp=0.0, max_retries=3):
    """
    Tries up to max_retries times. Each time it increases temperature by +0.2.
    Checks if the response starts with '{' and can be parsed as JSON.
    If successful, returns the raw response string; otherwise returns the last attempt.
    """
    temp = initial_temp
    r = ""
    for i in range(max_retries):
        r = get_field(prompt, temperature=temp)
        if r and r.startswith("{"):
            try:
                json.loads(r)
                return r
            except Exception:
                pass
        temp += 0.2
        logger.info(f"Retry {i+1}: New temperature={temp}")
    return r

def sanitize_summary_value(response: str, key="summary") -> str:
    """
    Replaces unescaped quotation marks in the JSON value for the given key.
    Helps fix JSON parse issues if the AI returns raw double quotes.
    """
    pattern = r'("'+re.escape(key)+r'":\s*")(.*?)(")'
    def replacer(match):
        prefix, value, suffix = match.groups()
        new_value = re.sub(r'(?<!\\)"', r'\"', value)
        return prefix + new_value + suffix
    sanitized_response = re.sub(pattern, replacer, response, flags=re.DOTALL)
    return sanitized_response

def parse_json_response(response: str, key: str, fallback="na") -> str:
    """
    Checks whether 'response' is valid JSON and extracts data[key].
    - If data[key] doesn't exist or is invalid, returns fallback.
    - If the AI returns a list (e.g. ["Bachelor","Lehramt"]), we join it into a single string.
    - If empty or just dots, we also fallback to 'na'.
    """
    resp_str = response.strip()
    if not resp_str or not resp_str.startswith("{"):
        logger.error(f"Response for {key} is not valid JSON. Response: '{resp_str}'")
        return fallback

    try:
        data = json.loads(resp_str)
        val = data.get(key, fallback)

        if isinstance(val, list):
            # If it's a list of strings, join them; else fallback
            if all(isinstance(x, str) for x in val):
                val = ", ".join(val)
                logger.info(f"Converted list of strings into a single string: {val}")
            else:
                logger.error(f"AI returned a list containing non-strings: {val}")
                return fallback

        if not isinstance(val, str):
            logger.error(f"AI returned a non-string {type(val)}: {val}")
            return fallback

        val_stripped = val.strip()
        if (not val_stripped 
            or re.fullmatch(r'[.\s…]+', val_stripped) 
            or val_stripped.lower() == "na"):
            logger.error(f"AI response for {key} is empty/insufficient: '{val}'")
            return fallback

        return val

    except Exception as e:
        logger.error(f"Error parsing {key}: {e}\nResponse was: '{resp_str}' - Attempting sanitize.")
        sanitized = sanitize_summary_value(resp_str, key)
        try:
            data2 = json.loads(sanitized)
            val2 = data2.get(key, fallback)

            if isinstance(val2, list):
                if all(isinstance(x, str) for x in val2):
                    val2 = ", ".join(val2)
                    logger.info(f"Converted list of strings to a single string (after sanitize): {val2}")
                else:
                    logger.error(f"After sanitize: List contains non-strings -> {val2}")
                    return fallback

            if not isinstance(val2, str):
                logger.error(f"After sanitize: type != str -> {val2}")
                return fallback

            val2s = val2.strip()
            if (not val2s 
                or re.fullmatch(r'[.\s…]+', val2s) 
                or val2s.lower() == "na"):
                logger.error(f"AI response (sanitized) for {key} is empty/dots: '{val2}'")
                return fallback

            return val2
        except Exception as e2:
            logger.error(f"Error parsing sanitized JSON: {e2}\nSanitized='{sanitized}'")
            return fallback


###############################################################################
# KI FUNCTION: get_document_summary (4 Prompt levels + fallback = 'na')
###############################################################################
def get_document_summary(pdf_content, language="de", temperature=0.0):
    """
    Provides a summary for a (possibly large) PDF.
    - If the PDF is short (< 15000 chars), we do the old 4-step logic.
    - If the PDF is large, we split it into chunks, get partial summaries,
      and merge them into a final summary.
    """
    text_length = len(pdf_content)

    # 1) Short / normal PDFs => old logic
    if text_length < 15000:
        if text_length < 50:
            logger.error("Extracted text is too short for summarization.")
            return "na"

        # 4-step prompt approach:
        if language == "de":
            prompt1 = (
                "Fasse den folgenden Text in 1–2 präzisen Sätzen zusammen. "
                "Nur reines JSON: {\"summary\":\"...\"}\n\n" + pdf_content
            )
            prompt2 = (
                "Erstelle bitte eine 1–2 Sätze Zusammenfassung als JSON {\"summary\":\"...\"}, "
                "ohne weitere Erklärungen.\n\n" + pdf_content
            )
            prompt3 = (
                "Text:\n" + pdf_content
                + "\n\nGib jetzt nur {\"summary\":\"...\"} zurück. "
                "Keine Entschuldigungen, keine Erklärungen!"
            )
            prompt4 = (
                "Achtung! Ich brauche reines JSON in der Form {\"summary\":\"...\"}. "
                "Hier der Text:\n\n" + pdf_content
            )
        else:
            # English version, analogous
            prompt1 = "Summarize #1...\n" + pdf_content
            prompt2 = "Summarize #2...\n" + pdf_content
            prompt3 = "Summarize #3...\n" + pdf_content
            prompt4 = "Summarize #4...\n" + pdf_content

        r1 = get_field_with_retry(prompt1, temperature, 3)
        s1 = parse_json_response(r1, "summary", "na")
        if s1 != "na":
            return s1

        logger.info("Summary: Prompt1 => fallback => Prompt2.")
        r2 = get_field_with_retry(prompt2, temperature + 0.2, 3)
        s2 = parse_json_response(r2, "summary", "na")
        if s2 != "na":
            return s2

        logger.info("Summary: Prompt2 => fallback => Prompt3.")
        r3 = get_field_with_retry(prompt3, temperature + 0.4, 3)
        s3 = parse_json_response(r3, "summary", "na")
        if s3 != "na":
            return s3

        logger.info("Summary: Prompt3 => fallback => Prompt4 (harder).")
        r4 = get_field_with_retry(prompt4, temperature + 0.6, 3)
        s4 = parse_json_response(r4, "summary", "na")
        if s4 != "na":
            return s4

        logger.error("All summary prompt levels failed => 'na'.")
        return "na"

    # 2) Large PDF => CHUNKING
    logger.info(f"PDF is very large ({text_length} characters). Starting chunking.")

    # e.g. chunk_size=8000, overlap=1000
    chunks = chunk_text(pdf_content, chunk_size=8000, overlap=1000)
    partial_summaries = []

    for i, chunk in enumerate(chunks):
        logger.info(f"Summarize Chunk {i+1}/{len(chunks)} (length={len(chunk)})")
        # Here, we do a simpler 1-step prompt (could be 4-step if you wish)
        if language == "de":
            chunk_prompt = (
                "Fasse den folgenden Text in 1–2 kurzen Sätzen zusammen. "
                "NUR reines JSON {\"summary\":\"...\"}, keine Erklärungen.\n\n"
                + chunk
            )
        else:
            chunk_prompt = (
                "Summarize the following text in 1–2 short sentences. "
                "Return ONLY {\"summary\":\"...\"} in JSON, no explanations.\n\n"
                + chunk
            )

        rc = get_field_with_retry(chunk_prompt, temperature, 3)
        sc = parse_json_response(rc, "summary", "na")
        if sc == "na":
            sc = ""  # fallback if chunk summary fails
        partial_summaries.append(sc)

    # Combine partial summaries:
    combined_text = " ".join(partial_summaries)
    logger.info(f"Creating final summary from {len(partial_summaries)} partial summaries.")

    # Final prompt => merges partial summaries
    if language == "de":
        final_prompt = (
            "Hier mehrere Teilzusammenfassungen eines langen Dokuments:\n"
            + combined_text
            + "\n\nFasse sie in 1–2 prägnanten Sätzen zusammen. "
            "Nur reines JSON {\"summary\":\"...\"}.\n"
        )
    else:
        final_prompt = (
            "Here are multiple partial summaries of a large document:\n"
            + combined_text
            + "\n\nCombine them into 1–2 concise sentences. "
            "Return ONLY {\"summary\":\"...\"} in JSON.\n"
        )

    r_final = get_field_with_retry(final_prompt, temperature + 0.2, 3)
    final_summary = parse_json_response(r_final, "summary", "na")

    return final_summary

###############################################################################
# KI FUNCTION: get_document_keywords
###############################################################################
def get_document_keywords(summary, language="de", temperature=0.0):
    """
    Queries the local LLM to extract 5–7 keywords from the given summary, 
    returning them as a JSON array. Attempts multiple prompts if necessary.
    """
    if language == "de":
        p1 = (
            "Extrahiere bitte 5–7 Schlüsselwörter aus dieser Zusammenfassung.\n"
            "Gib **ausschließlich** eine Ausgabe in der Form:\n\n"
            "{\"keywords\":[\"KW1\",\"KW2\", \"KW3\", \"KW4\"]}\n\n"
            "Beispiel (dein JSON soll genau so aussehen - mit anderen Keywords natürlich):\n"
            "{\"keywords\":[\"Bachelor\",\"Lehramt\",\"Gymnasien\",\"Abschluss\"]}\n\n"
            "Jetzt bitte NUR reines JSON, sonst nichts.\n"
            "Zusammenfassung:\n"
            + summary
        )

        p2 = (
            "Bitte NUR reines JSON in der Form:\n"
            "{\"keywords\":[\"KW1\",\"KW2\"]}\n"
            "Beispiel:\n{\"keywords\":[\"Bachelor\",\"Lehramt\",\"Gymnasien\"]}\n\n"
            "Hier die Zusammenfassung:\n"
            + summary
        )

        p3 = (
            "Hier die Zusammenfassung:\n" + summary
            + "\nNur reines JSON {\"keywords\":[\"word1\",\"word2\"]}!"
        )
        p4 = (
            "Achtung: reines JSON {\"keywords\":[...]} - NICHTS weiter!\n\n"
            + summary
        )
    else:
        # English placeholders
        p1 = "english #1 keywords..."
        p2 = "english #2 keywords..."
        p3 = "english #3 keywords..."
        p4 = "english #4 keywords..."

    r1 = get_field_with_retry(p1, temperature, 3)
    k1 = parse_json_response(r1, "keywords", "na")
    if k1 != "na":
        return k1

    logger.info("Keywords => Prompt2.")
    r2 = get_field_with_retry(p2, temperature+0.2, 3)
    k2 = parse_json_response(r2, "keywords", "na")
    if k2 != "na":
        return k2

    logger.info("Keywords => Prompt3.")
    r3 = get_field_with_retry(p3, temperature+0.4, 3)
    k3 = parse_json_response(r3, "keywords", "na")
    if k3 != "na":
        return k3

    logger.info("Keywords => Prompt4 (harder).")
    r4 = get_field_with_retry(p4, temperature+0.6, 3)
    k4 = parse_json_response(r4, "keywords", "na")
    if k4 != "na":
        return k4

    logger.error("Keywords - all attempts failed => 'na'.")
    return "na"

###############################################################################
# KI FUNCTION: get_document_category
###############################################################################
def get_document_category(summary, keywords, language="de", temperature=0.0):
    """
    Prompts the LLM to return a category as JSON { "category": "..." }.
    Attempts multiple fallback prompts if necessary.
    """
    if isinstance(keywords, list):
        keywords_joined = ", ".join(keywords)
    else:
        keywords_joined = keywords

    base_text = f"Zusammenfassung:\n{summary}\nKeywords:{keywords_joined}"
    if language == "de":
        p1 = (
            "Bestimme eine sinnvolle Kategorie als reines JSON.\n"
            "Gib **nur**:\n\n"
            "{\"category\":\"...\"}\n\n"
            "Beispiel:\n"
            "{\"category\":\"transcript\"}\n\n"
            "Keine weiteren Erklärungen, kein Drumherum, nur JSON. Text:\n" 
            + base_text
        )

        p2 = (
            "Bitte nur {\"category\":\"...\"} - ohne jede Zusätze:\n"
            + base_text
        )
        p3 = (
            base_text
            + "\n\nGib NUR {\"category\":\"...\"} zurück!"
        )
        p4 = (
            "ACHTUNG: reines JSON!\n"
            + base_text
        )
    else:
        # English placeholders
        p1 = "english cat p1..."
        p2 = "english cat p2..."
        p3 = "english cat p3..."
        p4 = "english cat p4..."

    r1 = get_field_with_retry(p1, temperature, 3)
    c1 = parse_json_response(r1, "category", "na")
    if c1 != "na":
        return c1

    logger.info("Cat => Prompt2")
    r2 = get_field_with_retry(p2, temperature+0.2, 3)
    c2 = parse_json_response(r2, "category", "na")
    if c2 != "na":
        return c2

    logger.info("Cat => Prompt3")
    r3 = get_field_with_retry(p3, temperature+0.4, 3)
    c3 = parse_json_response(r3, "category", "na")
    if c3 != "na":
        return c3

    logger.info("Cat => Prompt4 (harder)")
    r4 = get_field_with_retry(p4, temperature+0.6, 3)
    c4 = parse_json_response(r4, "category", "na")
    if c4 != "na":
        return c4

    logger.error("All category prompt levels => 'na'.")
    return "na"

###############################################################################
# KI FUNCTION: get_final_summary
###############################################################################
def get_final_summary(summary, keywords, category, language="de", temperature=0.0):
    """
    This function ultimately obtains the 'final_summary' that goes into the filename.
    We prompt for short keywords (1–2 words each), not full sentences.
    """

    if isinstance(keywords, list):
        kw_str = ", ".join(keywords)
    else:
        kw_str = keywords

    if isinstance(category, list):
        cat_str = ", ".join(category)
    else:
        cat_str = category

    base_text = f"Zusammenfassung: {summary}\nSchlagworte: {kw_str}\nKategorie: {cat_str}"

    if language == "de":
        p1 = (
            "Erstelle bitte bis zu 5 **Stichworte** (kurz! 1–2 Wörter pro Stichwort) "
            "als reines JSON.\nBeispiel:\n"
            "{\"final_summary\":\"bachelor,lehramt,bescheinigung\"}\n\n"
            "WICHTIG: Keine ganzen Sätze, nur kurze, prägnante Stichworte.\n"
            "NUR {\"final_summary\":\"...\"} zurückgeben, keine Erklärungen.\n\n"
            + base_text
        )

        p2 = (
            "Bitte **nur** reines JSON im Format {\"final_summary\":\"stichwort1,stichwort2\"}. "
            "Max. 5 Stichworte, **keine** ganzen Sätze!\n"
            "Beispiel:\n"
            "{\"final_summary\":\"krankmeldung,arbeitsunfaehigkeit,arztbesuch\"}\n\n"
            + base_text
        )

        p3 = (
            "Achtung! NUR die Form {\"final_summary\":\"...\"}. "
            "Keine Sätze, sondern nur kurze Stichworte!\n\n"
            + base_text
        )

        p4 = (
            "Letzter Versuch! Gib reines JSON {\"final_summary\":\"...\"} zurück.\n"
            "Bis zu 5 kurze Stichworte, KEINE Erläuterungen:\n\n"
            + base_text
        )
    else:
        # English placeholders
        p1 = (
            "Create up to 5 **short keywords** (1–2 words each) as pure JSON.\n"
            "Example:\n"
            "{\"final_summary\":\"bachelor,teaching,document\"}\n\n"
            "IMPORTANT: No full sentences, only short, concise keywords.\n"
            "Return ONLY {\"final_summary\":\"...\"}, no explanations.\n\n"
            + base_text
        )
        p2 = ...
        p3 = ...
        p4 = ...

    r1 = get_field_with_retry(p1, temperature, 3)
    f1 = parse_json_response(r1, "final_summary", "na")
    if f1 != "na":
        return f1

    logger.info("FinalSummary => Prompt2")
    r2 = get_field_with_retry(p2, temperature+0.2, 3)
    f2 = parse_json_response(r2, "final_summary", "na")
    if f2 != "na":
        return f2

    logger.info("FinalSummary => Prompt3")
    r3 = get_field_with_retry(p3, temperature+0.4, 3)
    f3 = parse_json_response(r3, "final_summary", "na")
    if f3 != "na":
        return f3

    logger.info("FinalSummary => Prompt4 (harder)")
    r4 = get_field_with_retry(p4, temperature+0.6, 3)
    f4 = parse_json_response(r4, "final_summary", "na")
    if f4 != "na":
        return f4

    logger.error("All final summary prompt levels => 'na'.")
    return "na"

###############################################################################
# ADDITIONAL HELPER FUNCTIONS (subtract tokens, clean, chunk, filter, etc.)
###############################################################################
def normalize_keywords(keyword_str):
    """
    Removes placeholders like '...', 'w1', 'w2', 'xxx', etc. 
    from the raw keywords to keep them clean.
    """
    if isinstance(keyword_str, list):
        joined = ",".join(keyword_str)
    else:
        joined = keyword_str
    tokens = [k.strip() for k in joined.split(",") if k.strip()]
    filtered = []
    for t in tokens:
        tl = t.lower()
        if tl in ("...", "…", "na", "xxx", "w1", "w2"):
            continue
        filtered.append(t)
    return ",".join(filtered[:7])

def tokens_similar(t1, t2):
    """
    Checks if two token strings are very similar (case-insensitive),
    or if one is a prefix of the other within ~2 chars difference.
    Used to remove duplicates when building final filenames.
    """
    t1, t2 = t1.lower(), t2.lower()
    if t1 == t2:
        return True
    if (t1.startswith(t2) or t2.startswith(t1)) and abs(len(t1)-len(t2)) <= 2:
        return True
    return False

def subtract_tokens(csv_str, remove_csv):
    """
    Splits the main tokens by '_', also splits the remove_csv tokens by '_',
    and removes any similar tokens from the main list.
    """
    tokens = [t.strip() for t in csv_str.split("_") if t.strip()]
    remove_tokens = [t.strip() for t in remove_csv.split("_") if t.strip()]
    result_tokens = []
    for token in tokens:
        if any(tokens_similar(token, rt) for rt in remove_tokens):
            continue
        result_tokens.append(token)
    return "_".join(result_tokens)

def convert_case(s, desired_case):
    """
    Converts tokens (split by '_') into the chosen case format:
    - camelCase
    - kebabCase
    - snakeCase
    - default fallback: kebabCase
    """
    words = s.split("_")
    if desired_case == "camelCase":
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])
    elif desired_case == "kebabCase":
        return "-".join(word.lower() for word in words)
    elif desired_case == "snakeCase":
        return "_".join(word.lower() for word in words)
    else:
        return "-".join(word.lower() for word in words)

def clean(text):
    """
    Trims whitespace, replaces German umlauts with ae, oe, ue, ss, 
    removes forbidden characters, and converts spaces to underscores.
    """
    text = text.strip()
    if not text:
        return "na"
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r'[\\/:*?"<>|]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text.lower()

def chunk_text(text: str, chunk_size=8000, overlap=1000) -> list:
    """
    Splits 'text' into multiple overlapping chunks of 'chunk_size' length in characters.
    'overlap' means how many characters from the end overlap with the next chunk.
    Returns a list of chunk strings.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # new start (with overlap)
        start = end - overlap
        if start < 0:
            start = 0

    return chunks

META_STOPWORDS = {
    "schlüsselwörter",
    "schluesselwoerter",
    "zusammenfassung",
    "summary",
    "keywords",
    "json",
    "beispiel",
    # possibly more, if you do not want them in filenames...
}

def filter_meta_words(text: str) -> str:
    """
    Removes certain undesired 'meta' words (e.g. 'schlüsselwörter', 'zusammenfassung'),
    which might come from AI prompts, so they don't appear in the filename.
    Case-insensitive filtering.
    """
    tokens = re.split(r'[\s,_-]+', text)
    filtered_tokens = []
    for t in tokens:
        t_lower = t.lower()
        if t_lower not in META_STOPWORDS:
            filtered_tokens.append(t)

    return "_".join(filtered_tokens)

###############################################################################
# GENERATE_FILENAME
###############################################################################
def generate_filename(
    pdf_content,
    language="de",
    dynamic_params=None,
    desired_case="kebabCase",
    override_category=None
):
    """
    Constructs the final filename in the format: DATE-CATEGORY-KEYWORDS-SUMMARY
    1) Extract date from content
    2) Query KI for summary, keywords
    3) Determine category via heuristic & KI
    4) Final short summary
    5) Filter out meta words, remove duplicates, convert case
    """

    # 1) DATE
    date_str = extract_date_from_content(pdf_content).replace("-", "")

    # 2) KI: SUMMARY, KEYWORDS
    summary = get_document_summary(pdf_content, language, 0.0)
    keywords_raw = get_document_keywords(summary, language, 0.0)
    keywords = normalize_keywords(keywords_raw)

    # 3) CATEGORY: heuristic + KI
    if override_category is not None:
        cat_final = override_category
    else:
        cat_ki = get_document_category(summary, keywords, language, 0.0)
        cat_heur = get_heuristic_category(pdf_content)
        cat_final = combine_categories(cat_ki, cat_heur)

    # 4) FINAL-SUMMARY => short keywords
    final_sum = get_final_summary(summary, keywords, cat_final, language, 0.0)
    if not isinstance(final_sum, str):
        final_sum = str(final_sum)

    # Filter out meta words
    keywords_filtered = filter_meta_words(keywords)
    final_sum_filtered = filter_meta_words(final_sum)

    # Truncate
    kw_tokens = [k.strip() for k in keywords_filtered.split(",") if k.strip()]
    truncated_keywords = "_".join(kw_tokens[:3])

    sum_tokens = [w.strip() for w in re.split(r'[,\s]+', final_sum_filtered) if w.strip()]
    sum_tokens_filt = [st for st in sum_tokens if st.lower() not in ("...", "w1", "w2", "xxx", "na")]
    truncated_summary = "_".join(sum_tokens_filt[:5])

    # Avoid repetition
    category_clean = clean(cat_final)
    truncated_keywords = subtract_tokens(truncated_keywords, category_clean)
    truncated_summary = subtract_tokens(truncated_summary, category_clean + "_" + truncated_keywords)

    formatted_category = convert_case(clean(cat_final), desired_case)
    formatted_keywords = convert_case(truncated_keywords, desired_case)
    formatted_summary = convert_case(truncated_summary, desired_case)

    # Project / Version
    dynamic_params = dynamic_params or {}
    project = dynamic_params.get("project", "").strip()
    version = dynamic_params.get("version", "").strip()
    project = project if project.lower() != "default" and project != "" else ""
    version = version if version.lower() != "default" and version != "" else ""

    formatted_project = convert_case(clean(project), desired_case) if project else ""
    formatted_version = convert_case(clean(version), desired_case) if version else ""

    parts = [date_str]
    if formatted_project:
        parts.append(formatted_project)
    parts.append(formatted_category)

    if formatted_keywords:
        parts.append(formatted_keywords)
    if formatted_summary:
        parts.append(formatted_summary)

    if formatted_version:
        parts.append(formatted_version)

    filename = "-".join(parts)
    filename = re.sub(r"-+", "-", filename).strip("-")
    if desired_case == "camelCase":
        filename = convert_case(filename.replace("-", "_"), "camelCase")
    return filename

###############################################################################
# rename_pdfs_in_directory
###############################################################################
def rename_pdfs_in_directory(
    directory,
    language="de",
    desired_case="kebabCase",
    dynamic_params=None
):
    """
    Renames all PDF files in the specified directory.
    1) Sort files by modification time (descending).
    2) Extract their text, generate a new filename,
       and rename them accordingly.
    3) Avoid collisions by adding _1, _2, etc.
    """
    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".pdf")
    ]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)

    for filename in files:
        filepath = os.path.join(directory, filename)
        logger.info(f"Processing file: {filepath}")

        pdf_content = pdfs_to_text_string(filepath)
        if not pdf_content.strip():
            logger.info("PDF appears to be empty. Skipping.")
            continue

        new_file_name = generate_filename(
            pdf_content,
            language=language,
            dynamic_params=dynamic_params,
            desired_case=desired_case,
            override_category=None
        )
        base_new_file_name = new_file_name
        counter = 1
        new_filepath = os.path.join(directory, new_file_name + ".pdf")

        while os.path.exists(new_filepath):
            new_file_name = f"{base_new_file_name}_{counter}"
            new_filepath = os.path.join(directory, new_file_name + ".pdf")
            counter += 1

        try:
            os.rename(filepath, new_filepath)
            logger.info(f"Renamed '{filename}' to '{new_filepath}'")
        except Exception as e:
            logger.error(f"Error renaming '{filename}': {e}")

###############################################################################
# main()
###############################################################################
def main():
    """
    Entry point. Interactively gets:
    - Directory path
    - Language (de / en)
    - Desired case format (kebab, camel, snake)
    - Optional project and version
    Then calls rename_pdfs_in_directory.
    """
    dir_input = input("Path to the directory with PDFs (default: ./input_files): ").strip()
    if not dir_input:
        dir_input = "./input_files"

    lang = input("Language (de/en, default: de): ").strip().lower() or "de"
    dcase = input("Desired case format (camelCase, kebabCase, snakeCase, default: kebabCase): ").strip() or "kebabCase"

    project = input("Project name (optional): ").strip()
    version = input("Version (optional): ").strip()

    dynp = {}
    if project:
        dynp["project"] = project
    if version:
        dynp["version"] = version

    rename_pdfs_in_directory(
        directory=dir_input,
        language=lang,
        desired_case=dcase,
        dynamic_params=dynp
    )

if __name__ == "__main__":
    main()
```
