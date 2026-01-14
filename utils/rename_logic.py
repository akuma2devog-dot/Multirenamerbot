import re

def parse_rename(text: str):
    """
    Supports:
    Naruto S1E
    Naruto | S2E15
    """
    base = text
    season = 1
    start_ep = 1

    if "|" in text:
        base, tag = [x.strip() for x in text.split("|", 1)]
    else:
        tag = text

    match = re.search(r"S(\d+)E(\d*)", tag)
    if match:
        season = int(match.group(1))
        start_ep = int(match.group(2)) if match.group(2) else 1

    return base.strip(), season, start_ep
