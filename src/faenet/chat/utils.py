import re

# Matches common Unicode emoji: emoticons, symbols, dingbats, supplemental symbols,
# variation selectors, zero-width joiners, skin tone modifiers, and flag sequences.
_EMOJI_RE = re.compile(
    "^("
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"    # misc symbols & pictographs
    "\U0001F680-\U0001F6FF"    # transport & map
    "\U0001F900-\U0001F9FF"    # supplemental symbols
    "\U0001FA00-\U0001FA6F"    # chess symbols
    "\U0001FA70-\U0001FAFF"    # symbols extended-A
    "\U00002702-\U000027B0"    # dingbats
    "\U0000FE0F"               # variation selector-16
    "\U0000200D"               # zero-width joiner
    "\U0001F1E0-\U0001F1FF"    # regional indicators (flags)
    "\U00002600-\U000026FF"    # misc symbols
    "\U00002300-\U000023FF"    # misc technical
    "\U0000200B-\U0000200D"    # zero-width chars
    "\U0000E0020-\U0000E007F"  # tags (flag subdivisions)
    "\U0001F3FB-\U0001F3FF"    # skin tone modifiers
    "]+)$"
)


def is_valid_emoji(text):
    """Return True if text is a valid emoji (no HTML/script injection)."""
    if not text or len(text) > 8:
        return False
    return bool(_EMOJI_RE.match(text))
