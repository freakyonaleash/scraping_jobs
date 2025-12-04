import pandas as pd
import re
from urllib.parse import urlparse

# Try to load spaCy and the small English model
try:
    import spacy
    try:
        NER_NLP = spacy.load("en_core_web_sm")
        NER_AVAILABLE = True
    except OSError:
        print("[WARN] spaCy model 'en_core_web_sm' not found. Run:")
        print("       python -m spacy download en_core_web_sm")
        NER_NLP = None
        NER_AVAILABLE = False
except ImportError:
    print("[WARN] spaCy is not installed. Run:")
    print("       pip install spacy")
    NER_NLP = None
    NER_AVAILABLE = False

# --------------- config ---------------

INPUT_FILE = "CleanData.csv"
OUTPUT_FILE = "QA_OrgOnly.csv"
QA_CATEGORY_VALUE = "QA Testing"

# Names we never treat as client orgs
ORG_BLOCKLIST = {
    "upwork", "google", "gmail", "notion", "jira", "atlassian", "github",
    "figma", "stripe", "paypal", "braintree", "facebook", "instagram",
    "whatsapp", "shopify", "trustly", "browserstack", "postman",
}

# Domains we never treat as client orgs
DOMAIN_BLOCKLIST = {
    "upwork.com", "google.com", "gmail.com", "docs.google.com",
    "notion.so", "jira.com", "atlassian.com", "github.com",
    "figma.com", "stripe.com", "paypal.com", "braintreepayments.com",
    "facebook.com", "instagram.com", "whatsapp.com", "shopify.com",
}

# Company suffixes to strip
COMPANY_SUFFIXES = [
    " inc", " inc.", " llc", " ltd", " gmbh", " sas", " srl", " bv", " plc",
]


# --------------- helpers: generic ---------------

def extract_urls(text: str):
    if not text:
        return []
    url_pattern = re.compile(
        r"(https?://[^\s]+|www\.[^\s]+|\b[\w.-]+\.(?:com|io|ai|co|net|org|app)\b)",
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


def domain_from_url(raw_url: str):
    if not raw_url:
        return None
    url = raw_url
    if not url.startswith("http"):
        url = "http://" + url
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return None


def normalize_org_name(raw: str):
    if not raw:
        return ""
    name = raw.strip()

    # drop surrounding quotes
    if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
        name = name[1:-1].strip()

    # if short token then parentheses, keep token before "("
    if "(" in name and ")" in name:
        before_paren = name.split("(", 1)[0].strip()
        if before_paren:
            name = before_paren

    name = name.lower().strip()

    # remove trailing punctuation
    name = name.rstrip(".,;: ")

    # strip company suffixes
    for suf in COMPANY_SUFFIXES:
        if name.endswith(suf):
            name = name[: -len(suf)].rstrip()

    # fix spaced TLDs
    replacements = [
        (" .ai", ".ai"), (". ai", ".ai"),
        (" .io", ".io"), (". io", ".io"),
        (" .co", ".co"), (". co", ".co"),
    ]
    for old, new in replacements:
        name = name.replace(old, new)

    # collapse spaces
    name = re.sub(r"\s+", " ", name)

    return name


def looks_like_org_token(token: str):
    if not token:
        return False
    t = token.strip().strip(",.")
    if not t:
        return False
    lower = t.lower()
    if lower in {"we", "our", "company", "agency", "firm", "startup"}:
        return False
    if not re.search(r"[a-zA-Z]", t):
        return False
    if t[0].isupper() or any(
        ext in t.lower()
        for ext in [".ai", ".io", ".co", "labs", "studio", "consulting", "digital"]
    ):
        return True
    return False


# --------------- helpers: rule based org extraction ---------------

def org_from_header_lines(description: str):
    """
    Look at first few non empty lines.
    If a line looks like a single company name like 'TradeCafe',
    treat it as org with high confidence.
    """
    if not description:
        return None, "none"
    lines = [ln.strip() for ln in description.splitlines()]
    non_empty = [ln for ln in lines if ln]
    for ln in non_empty[:5]:
        # break on section headers
        if ln.lower() in {"about us", "summary"}:
            break
        parts = ln.split()
        if 1 <= len(parts) <= 3:
            if ln.lower() in {"remote", "full time", "full time remote", "job summary"}:
                continue
            if looks_like_org_token(parts[0]):
                return ln, "high"
    return None, "none"


def org_from_is_pattern(intro_orig: str):
    """
    Pattern: X is ...
    Example: 'TradeCafe is revolutionizing...'
    """
    # limit to first 600 chars
    text = intro_orig[:600]
    for m in re.finditer(r"\b([A-Z][\w.& ]{0,40})\s+is\b", text):
        candidate = m.group(1).strip()
        norm = normalize_org_name(candidate)
        if not norm or norm in ORG_BLOCKLIST:
            continue
        if looks_like_org_token(candidate.split()[-1]):
            return candidate, "high"
    return None, "none"


def org_from_at_pattern(intro_orig: str):
    """
    Pattern: At X, we ...
    Example: 'At LeadFlow, we help...'
    """
    m = re.search(r"At\s+(.{1,40}?),\s+we\b", intro_orig)
    if m:
        candidate = m.group(1).strip()
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST:
            return candidate, "high"
    return None, "none"


LOOKING_PHRASES = [
    " is looking", " are looking",
    " is seeking", " are seeking",
    " is in need of", " are in need of",
    " is searching", " are searching",
    " is hiring", " are hiring",
]


def org_from_seeking_pattern(intro_orig: str):
    """
    Pattern: X is looking / seeking / in need of / searching / hiring
    Example: 'ModMarket is seeking experienced QA experts...'
    """
    low = intro_orig.lower()
    for phrase in LOOKING_PHRASES:
        idx = low.find(phrase)
        if idx == -1:
            continue
        before = intro_orig[:idx].rstrip()
        before_tail = before[-40:]
        tokens = before_tail.split()
        if not tokens:
            continue
        # drop leading "We", "Our"
        while tokens and tokens[0].lower() in {"we", "our"}:
            tokens = tokens[1:]
        if not tokens:
            continue
        candidate = " ".join(tokens[-3:]).strip(",. ")
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST and looks_like_org_token(candidate.split()[0]):
            return candidate, "high"
    return None, "none"


def org_from_our_company_pattern(intro_orig: str):
    """
    Pattern: Our company X ..., Our agency X ...
    """
    m = re.search(r"Our (company|agency|firm)\s+([A-Z][^,\.]+)", intro_orig)
    if m:
        candidate = m.group(2).strip(" ,.")
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST:
            return candidate, "high"
    m = re.search(r"Our (company|agency|firm)\s*,\s*([^,]+),", intro_orig)
    if m:
        candidate = m.group(2).strip(" ,.")
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST:
            return candidate, "high"
    return None, "none"


def org_from_we_are_pattern(intro_orig: str):
    """
    Pattern: We are X, ...
    Example: 'We are SocialToast.ai, one of...'
    """
    m = re.search(r"We are\s+(.{1,40}?)[,\.]", intro_orig)
    if m:
        candidate = m.group(1).strip()
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST and looks_like_org_token(candidate.split()[0]):
            return candidate, "medium"
    return None, "none"


def org_from_website_pattern(description: str):
    """
    Pattern: look at the app / website here: URL
    Use domain or matching product name as org.
    """
    if not description:
        return None, "none"

    urls = extract_urls(description)
    for url in urls:
        domain = domain_from_url(url)
        if not domain or domain in DOMAIN_BLOCKLIST:
            continue
        sld = domain.split(".")[0]  # second level
        # try to find a product name containing SLD
        # simple heuristic: capitalized word or two where SLD appears
        m = re.search(r"\b([A-Z][\w]*(?:\s+(?:Studio|Labs|App|Platform))?)\b", description)
        candidate = None
        if m:
            token = m.group(1)
            if sld.lower() in token.lower():
                candidate = token.strip()
        if not candidate:
            candidate = domain
        norm = normalize_org_name(candidate)
        if norm and norm not in ORG_BLOCKLIST:
            return candidate, "medium"
    return None, "none"


# --------------- helpers: ML org extraction (spaCy NER) ---------------

def ml_org_candidate(text: str):
    """
    Use spaCy NER to find an ORG entity in the intro.
    Only used as fallback when rules fail.
    """
    if not NER_AVAILABLE or not text:
        return None
    doc = NER_NLP(text[:400])
    for ent in doc.ents:
        if ent.label_ == "ORG":
            candidate = ent.text.strip()
            norm = normalize_org_name(candidate)
            if norm and norm not in ORG_BLOCKLIST:
                return candidate
    return None


# --------------- helpers: org type ---------------

def classify_org_type(full_text: str, org_name_norm: str, confidence: str):
    """
    Simple org type classifier based on text.
    """
    if confidence == "none" or not full_text:
        return "individual_or_undefined"

    low = full_text.lower()

    if any(w in low for w in ["agency", "consulting firm", "consultancy", "advisory partners", "outsourced cto"]):
        return "agency"

    if any(w in low for w in ["platform", "marketplace", "saas", "software product", "app ", "application", "tool"]):
        return "product_company"

    if "our client is" in low or "on behalf of our client" in low:
        return "end_client_business"

    return "individual_or_undefined"


# --------------- main org extraction for one row ---------------

def extract_org_fields(title: str, description: str):
    """
    Returns OrgNameRaw, OrgNameNormalized, OrgConfidence, OrgType
    """
    title = title or ""
    desc = description or ""

    # intro for rule patterns
    intro_orig = desc[:600]

    # 1 header line pattern
    org_raw, org_conf = org_from_header_lines(desc)

    # 2 "X is ..." pattern
    if not org_raw:
        org_raw, org_conf = org_from_is_pattern(intro_orig)

    # 3 "At X, we" pattern
    if not org_raw:
        org_raw, org_conf = org_from_at_pattern(intro_orig)

    # 4 "X is seeking / looking / hiring" pattern
    if not org_raw:
        org_raw, org_conf = org_from_seeking_pattern(intro_orig)

    # 5 "Our company X" pattern
    if not org_raw:
        org_raw, org_conf = org_from_our_company_pattern(intro_orig)

    # 6 "We are X," pattern
    if not org_raw:
        org_raw, org_conf = org_from_we_are_pattern(intro_orig)

    # 7 website pattern
    if not org_raw:
        org_raw, org_conf = org_from_website_pattern(desc)

    # 8 ML fallback with spaCy NER
    if not org_raw:
        candidate = ml_org_candidate(title + " " + desc)
        if candidate:
            org_raw = candidate
            org_conf = "medium"

    # Normalize and classify
    org_norm = normalize_org_name(org_raw) if org_raw else ""

    full_text = title + "\n" + desc
    org_type = classify_org_type(full_text, org_norm, org_conf)

    # blocklist guard
    if org_norm in ORG_BLOCKLIST:
        org_raw = ""
        org_norm = ""
        org_conf = "none"
        org_type = "individual_or_undefined"

    if not org_conf:
        org_conf = "none"

    return org_raw, org_norm, org_conf, org_type


# --------------- main script ---------------

def main():
    print(f"[INFO] Loading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    print("[INFO] Filtering QA Testing rows...")
    qa = df[df["Category"] == QA_CATEGORY_VALUE].copy()

    if qa.empty:
        print("[WARN] No rows with Category == 'QA Testing' found.")
        return

    qa["OrgNameRaw"] = ""
    qa["OrgNameNormalized"] = ""
    qa["OrgConfidence"] = ""
    qa["OrgType"] = ""

    print(f"[INFO] Extracting organizations for {len(qa)} QA rows...")
    for idx, row in qa.iterrows():
        title = row.get("Title", "")
        description = row.get("Description", "")
        org_raw, org_norm, org_conf, org_type = extract_org_fields(title, description)
        qa.at[idx, "OrgNameRaw"] = org_raw
        qa.at[idx, "OrgNameNormalized"] = org_norm
        qa.at[idx, "OrgConfidence"] = org_conf
        qa.at[idx, "OrgType"] = org_type

    print(f"[INFO] Saving to {OUTPUT_FILE}...")
    qa.to_csv(OUTPUT_FILE, index=False)
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
