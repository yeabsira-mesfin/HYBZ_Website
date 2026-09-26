"""Defense in depth. Heuristics are signals, never an authorization boundary."""
import re


PATTERNS = [
    re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
]
INJECTION = re.compile(
    r'ignore\s+(all\s+)?(previous|prior|system)\s+instructions|'
    r'(reveal|print|show)\s+(the\s+)?system\s+prompt|'
    r'\b(exfiltrate|override permissions)\b|<\|im_start\|>|\[INST\]', re.I)


def redact(text):
    for pattern in PATTERNS:
        text = pattern.sub('[REDACTED]', text)
    return text


def suspicious(text):
    return bool(INJECTION.search(text))
