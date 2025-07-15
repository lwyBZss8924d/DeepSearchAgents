"""
Script to verify and optionally update arXiv category taxonomy.
"""

import json
from pathlib import Path
from .categories import CATEGORIES

TAXONOMY_FILE = Path(__file__).parent / "taxonomy.json"


def update_taxonomy_file():
    """
    Create taxonomy.json from the built-in categories.
    Returns the taxonomy dictionary.
    """
    print(f"Creating taxonomy file at {TAXONOMY_FILE}...")
    with open(TAXONOMY_FILE, 'w', encoding='utf-8') as f:
        json.dump(CATEGORIES, f, indent=2, ensure_ascii=False)
    print("Done!")
    return CATEGORIES


def load_taxonomy() -> dict:
    """
    Load taxonomy from the JSON file.
    If file doesn't exist, create it from built-in categories.
    """
    if not TAXONOMY_FILE.exists():
        print(f"Taxonomy file not found at {TAXONOMY_FILE}, creating it...")
        return update_taxonomy_file()

    print(f"Loading taxonomy from {TAXONOMY_FILE}")
    with open(TAXONOMY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    # When run directly, create/update the taxonomy file
    print("Creating taxonomy file from built-in categories...")
    taxonomy = update_taxonomy_file()
    print(f"\nCreated taxonomy with {len(taxonomy)} primary categories:")
    for primary, data in taxonomy.items():
        print(f"- {primary}: {data['name']} ({len(data['subcategories'])} subcategories)")
