"""Name Normalization Utility

Standardizes player names across different data sources to ensure consistency.
Handles common variations like suffixes (Jr., II, III), extra spaces, and special characters.

Usage:
    from utils.name_normalizer import normalize_player_name, fuzzy_match_names

    normalized = normalize_player_name("Gardner Minshew II")  # -> "Gardner Minshew"
    is_match = fuzzy_match_names("Gardner  Minshew", "Gardner Minshew II")  # -> True
"""

import re
from typing import Optional
from difflib import SequenceMatcher


# Common name suffixes to remove for normalization
NAME_SUFFIXES = [
    'Jr.', 'Jr', 'JR',
    'Sr.', 'Sr', 'SR',
    'II', 'III', 'IV', 'V',
    '2nd', '3rd', '4th', '5th'
]


def normalize_player_name(name: str) -> str:
    """
    Normalize a player name to a standard format.

    Normalization steps:
    1. Strip leading/trailing whitespace
    2. Collapse multiple spaces to single space
    3. Remove common suffixes (Jr., II, III, etc.)
    4. Remove periods from initials (e.g., "A.J." -> "AJ")
    5. Title case (preserve existing case for acronyms)

    Args:
        name: Raw player name

    Returns:
        Normalized player name

    Examples:
        >>> normalize_player_name("Gardner Minshew II")
        'Gardner Minshew'
        >>> normalize_player_name("Gardner  Minshew")
        'Gardner Minshew'
        >>> normalize_player_name("A.J. Brown")
        'AJ Brown'
        >>> normalize_player_name("Patrick Mahomes Jr.")
        'Patrick Mahomes'
    """
    if not name:
        return ""

    # Step 1: Strip and collapse spaces
    normalized = ' '.join(name.strip().split())

    # Step 2: Remove suffixes
    # Create regex pattern for suffix removal
    suffix_pattern = r'\s+(' + '|'.join(re.escape(s) for s in NAME_SUFFIXES) + r')\.?$'
    normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)

    # Step 3: Remove periods from initials but preserve spacing
    # This handles "A.J. Brown" -> "AJ Brown"
    normalized = re.sub(r'([A-Z])\.(?=[A-Z]\.?\s)', r'\1', normalized)
    normalized = re.sub(r'([A-Z])\.(\s)', r'\1\2', normalized)

    # Step 4: Final cleanup - ensure single spaces
    normalized = ' '.join(normalized.split())

    return normalized.strip()


def fuzzy_match_names(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Check if two player names are likely the same person using fuzzy matching.

    This is useful for matching names that might have slight variations like:
    - Different suffixes: "Gardner Minshew" vs "Gardner Minshew II"
    - Extra spaces: "Gardner  Minshew" vs "Gardner Minshew"
    - Spelling variations: "A.J. Brown" vs "AJ Brown"

    Args:
        name1: First player name
        name2: Second player name
        threshold: Similarity threshold (0.0-1.0). Default 0.85 means 85% similar

    Returns:
        True if names are likely the same player

    Examples:
        >>> fuzzy_match_names("Gardner Minshew", "Gardner Minshew II")
        True
        >>> fuzzy_match_names("Patrick Mahomes", "Josh Allen")
        False
    """
    # First try exact match on normalized names (fast path)
    norm1 = normalize_player_name(name1)
    norm2 = normalize_player_name(name2)

    if norm1 == norm2:
        return True

    # If not exact match, use fuzzy matching
    similarity = SequenceMatcher(None, norm1.lower(), norm2.lower()).ratio()
    return similarity >= threshold


def get_name_variants(name: str) -> list[str]:
    """
    Generate common variants of a player name for lookup purposes.

    This is useful when querying databases where the exact name format is unknown.

    Args:
        name: Player name

    Returns:
        List of possible name variants

    Examples:
        >>> get_name_variants("Gardner Minshew")
        ['Gardner Minshew', 'Gardner Minshew II', 'Gardner Minshew Jr.', ...]
    """
    normalized = normalize_player_name(name)
    variants = {normalized}

    # Add common suffix variations
    common_suffixes = ['II', 'III', 'Jr.', 'Sr.']
    for suffix in common_suffixes:
        variants.add(f"{normalized} {suffix}")

    return sorted(list(variants))


def batch_normalize_names(names: list[str]) -> dict[str, str]:
    """
    Normalize a batch of names and return mapping of original -> normalized.

    Useful for bulk updates or analysis.

    Args:
        names: List of player names

    Returns:
        Dictionary mapping original name -> normalized name

    Examples:
        >>> batch_normalize_names(["Gardner Minshew II", "Patrick Mahomes Jr."])
        {'Gardner Minshew II': 'Gardner Minshew', 'Patrick Mahomes Jr.': 'Patrick Mahomes'}
    """
    return {name: normalize_player_name(name) for name in names}


if __name__ == '__main__':
    # Test cases
    print("Testing Name Normalization Utility\n" + "="*50)

    test_cases = [
        "Gardner Minshew II",
        "Gardner  Minshew",  # Double space
        "Patrick Mahomes Jr.",
        "A.J. Brown",
        "C.J. Stroud",
        "Geno  Smith",  # Double space
        "Tommy Devito",
        "Kenny Pickett III",
    ]

    print("\n1. Name Normalization:")
    for name in test_cases:
        normalized = normalize_player_name(name)
        print(f"  '{name}' -> '{normalized}'")

    print("\n2. Fuzzy Matching:")
    match_tests = [
        ("Gardner Minshew", "Gardner Minshew II"),
        ("Gardner  Minshew", "Gardner Minshew"),
        ("Patrick Mahomes", "Patrick Mahomes Jr."),
        ("Patrick Mahomes", "Josh Allen"),  # Should be False
    ]

    for name1, name2 in match_tests:
        is_match = fuzzy_match_names(name1, name2)
        print(f"  '{name1}' vs '{name2}': {is_match}")

    print("\n3. Name Variants:")
    for name in ["Gardner Minshew", "Patrick Mahomes"]:
        variants = get_name_variants(name)
        print(f"  '{name}': {variants[:3]}...")  # Show first 3
