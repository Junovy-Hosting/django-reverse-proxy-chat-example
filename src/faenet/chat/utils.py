import re

# Matches common Unicode emoji: emoticons, symbols, dingbats, supplemental symbols,
# variation selectors, zero-width joiners, skin tone modifiers, and flag sequences.
_EMOJI_RE = re.compile(
    "^("
    "[\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # misc symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "\U0001fa00-\U0001fa6f"  # chess symbols
    "\U0001fa70-\U0001faff"  # symbols extended-A
    "\U00002702-\U000027b0"  # dingbats
    "\U0000fe0f"  # variation selector-16
    "\U0000200d"  # zero-width joiner
    "\U0001f1e0-\U0001f1ff"  # regional indicators (flags)
    "\U00002600-\U000026ff"  # misc symbols
    "\U00002300-\U000023ff"  # misc technical
    "\U0000200b-\U0000200d"  # zero-width chars
    "\U0000e0020-\U0000e007F"  # tags (flag subdivisions)
    "\U0001f3fb-\U0001f3ff"  # skin tone modifiers
    "]+)$"
)


def is_valid_emoji(text):
    """Return True if text is a valid emoji (no HTML/script injection)."""
    if not text or len(text) > 8:
        return False
    return bool(_EMOJI_RE.match(text))
