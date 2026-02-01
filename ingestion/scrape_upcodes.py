"""
UpCodes NYC Building Codes Scraper
===================================

This script scrapes NYC building code content from UpCodes.
It extracts chapter-by-chapter content and saves it as text files
for ingestion into the RAG database.

Requirements:
- requests
- beautifulsoup4

Run: pip install requests beautifulsoup4
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

# =============================================================================
# CONFIGURATION
# =============================================================================

# Output directory for scraped content
OUTPUT_DIR = Path(__file__).parent / "scraped_codes"

# Base URL for UpCodes
BASE_URL = "https://up.codes/viewer/new_york_city"

# All NYC codes to scrape with their chapters
NYC_CODES = {
    "nyc-building-code-2022": {
        "name": "NYC Building Code 2022",
        "chapters": [
            {"num": "1", "slug": "administration"},
            {"num": "2", "slug": "definitions"},
            {"num": "3", "slug": "use-and-occupancy-classification"},
            {"num": "4", "slug": "special-detailed-requirements-based-on-use-and-occupancy"},
            {"num": "5", "slug": "general-building-heights-and-areas"},
            {"num": "6", "slug": "types-of-construction"},
            {"num": "7", "slug": "fire-and-smoke-protection-features"},
            {"num": "8", "slug": "interior-finishes"},
            {"num": "9", "slug": "fire-protection-systems"},
            {"num": "10", "slug": "means-of-egress"},
            {"num": "11", "slug": "accessibility"},
            {"num": "12", "slug": "interior-environment"},
            {"num": "13", "slug": "energy-efficiency"},
            {"num": "14", "slug": "exterior-walls"},
            {"num": "15", "slug": "roof-assemblies-and-rooftop-structures"},
            {"num": "16", "slug": "structural-design"},
            {"num": "17", "slug": "special-inspections-and-tests"},
            {"num": "18", "slug": "soils-and-foundations"},
            {"num": "19", "slug": "concrete"},
            {"num": "20", "slug": "aluminum"},
            {"num": "21", "slug": "masonry"},
            {"num": "22", "slug": "steel"},
            {"num": "23", "slug": "wood"},
            {"num": "24", "slug": "glass-and-glazing"},
            {"num": "25", "slug": "gypsum-board-and-plaster"},
            {"num": "26", "slug": "plastic"},
            {"num": "27", "slug": "electrical"},
            {"num": "28", "slug": "mechanical-systems"},
            {"num": "29", "slug": "plumbing-systems"},
            {"num": "30", "slug": "elevators-and-conveying-systems"},
            {"num": "31", "slug": "special-construction"},
            {"num": "32", "slug": "encroachments-into-the-public-right-of-way"},
            {"num": "33", "slug": "safeguards-during-construction-or-demolition"},
            {"num": "35", "slug": "referenced-standards"},
        ]
    },
    "nyc-mechanical-code-2022": {
        "name": "NYC Mechanical Code 2022",
        "chapters": [
            {"num": "1", "slug": "administration"},
            {"num": "2", "slug": "definitions"},
            {"num": "3", "slug": "general-regulations"},
            {"num": "4", "slug": "ventilation"},
            {"num": "5", "slug": "exhaust-systems"},
            {"num": "6", "slug": "duct-systems"},
            {"num": "7", "slug": "combustion-air"},
            {"num": "8", "slug": "chimneys-and-vents"},
            {"num": "9", "slug": "specific-appliances-fireplaces-and-solid-fuel-burning-equipment"},
            {"num": "10", "slug": "boilers-water-heaters-and-pressure-vessels"},
            {"num": "11", "slug": "refrigeration"},
            {"num": "12", "slug": "hydronic-piping"},
            {"num": "13", "slug": "fuel-oil-piping-and-storage"},
            {"num": "14", "slug": "solar-systems"},
            {"num": "15", "slug": "referenced-standards"},
        ]
    },
    "nyc-plumbing-code-2022": {
        "name": "NYC Plumbing Code 2022",
        "chapters": [
            {"num": "1", "slug": "administration"},
            {"num": "2", "slug": "definitions"},
            {"num": "3", "slug": "general-regulations"},
            {"num": "4", "slug": "fixtures-faucets-and-fixture-fittings"},
            {"num": "5", "slug": "water-heaters"},
            {"num": "6", "slug": "water-supply-and-distribution"},
            {"num": "7", "slug": "sanitary-drainage"},
            {"num": "8", "slug": "indirect-special-waste"},
            {"num": "9", "slug": "vents"},
            {"num": "10", "slug": "traps-and-interceptors"},
            {"num": "11", "slug": "storm-drainage"},
            {"num": "12", "slug": "special-piping-and-storage-systems"},
            {"num": "13", "slug": "nonpotable-water-systems"},
            {"num": "14", "slug": "referenced-standards"},
        ]
    },
    "nyc-fuel-gas-code-2022": {
        "name": "NYC Fuel Gas Code 2022",
        "chapters": [
            {"num": "1", "slug": "administration"},
            {"num": "2", "slug": "definitions"},
            {"num": "3", "slug": "general-regulations"},
            {"num": "4", "slug": "gas-piping-installations"},
            {"num": "5", "slug": "chimneys-and-vents"},
            {"num": "6", "slug": "specific-appliances"},
            {"num": "7", "slug": "gaseous-hydrogen-systems"},
            {"num": "8", "slug": "referenced-standards"},
        ]
    },
    "nyc-fire-code-2022": {
        "name": "NYC Fire Code 2022",
        "chapters": [
            {"num": "1", "slug": "administration"},
            {"num": "2", "slug": "definitions"},
            {"num": "3", "slug": "general-requirements"},
            {"num": "4", "slug": "emergency-planning-and-preparedness"},
            {"num": "5", "slug": "fire-service-features"},
            {"num": "6", "slug": "building-services-and-systems"},
            {"num": "7", "slug": "fire-resistance-rated-construction"},
            {"num": "8", "slug": "interior-finish-decorative-materials-and-furnishings"},
            {"num": "9", "slug": "fire-protection-systems"},
            {"num": "10", "slug": "means-of-egress"},
            {"num": "11", "slug": "construction-requirements-for-existing-buildings"},
            {"num": "20", "slug": "aviation-facilities"},
            {"num": "21", "slug": "dry-cleaning"},
            {"num": "22", "slug": "combustible-dust-producing-operations"},
            {"num": "23", "slug": "motor-fuel-dispensing-facilities-and-repair-garages"},
            {"num": "24", "slug": "flammable-finishes"},
            {"num": "25", "slug": "fruit-and-crop-ripening"},
            {"num": "26", "slug": "fumigation-and-insecticidal-fogging"},
            {"num": "27", "slug": "semiconductor-fabrication-facilities"},
            {"num": "28", "slug": "lumber-yards-and-agro-industrial-solid-biomass-and-woodworking-facilities"},
            {"num": "29", "slug": "manufacture-of-organic-coatings"},
            {"num": "30", "slug": "industrial-ovens"},
            {"num": "31", "slug": "tents-and-other-membrane-structures"},
            {"num": "32", "slug": "high-piled-combustible-storage"},
            {"num": "33", "slug": "fire-safety-during-construction-and-demolition"},
            {"num": "34", "slug": "tire-rebuilding-and-tire-storage"},
            {"num": "35", "slug": "welding-and-other-hot-work"},
            {"num": "36", "slug": "marinas"},
            {"num": "37", "slug": "combustible-fibers"},
            {"num": "38", "slug": "liquefied-petroleum-gases"},
            {"num": "39", "slug": "processing-and-extraction-facilities"},
            {"num": "50", "slug": "hazardous-materials-general-provisions"},
            {"num": "51", "slug": "aerosols"},
            {"num": "53", "slug": "compressed-gases"},
            {"num": "54", "slug": "corrosive-materials"},
            {"num": "55", "slug": "cryogenic-fluids"},
            {"num": "56", "slug": "explosives-and-fireworks"},
            {"num": "57", "slug": "flammable-and-combustible-liquids"},
            {"num": "58", "slug": "flammable-gases-and-flammable-cryogenic-fluids"},
            {"num": "59", "slug": "flammable-solids"},
            {"num": "60", "slug": "highly-toxic-and-toxic-materials"},
            {"num": "61", "slug": "liquefied-natural-gas"},
            {"num": "62", "slug": "organic-peroxides"},
            {"num": "63", "slug": "oxidizers-oxidizing-gases-and-oxidizing-cryogenic-fluids"},
            {"num": "64", "slug": "pyrophoric-materials"},
            {"num": "65", "slug": "pyroxylin-plastics"},
            {"num": "66", "slug": "unstable-reactive-materials"},
            {"num": "67", "slug": "water-reactive-solids-and-liquids"},
            {"num": "80", "slug": "referenced-standards"},
        ]
    },
}

# Request headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

def fetch_chapter(code_slug: str, chapter_slug: str) -> str:
    """Fetch the HTML content of a chapter page."""
    url = f"{BASE_URL}/{code_slug}/chapter/{chapter_slug}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"    ERROR fetching {url}: {e}")
        return None


def parse_chapter_content(html: str) -> List[Dict[str, Any]]:
    """
    Parse the HTML and extract code sections.
    Returns a list of sections with their content.
    """
    soup = BeautifulSoup(html, 'html.parser')
    sections = []

    # Find the main content area
    # UpCodes uses various div structures, we'll try to find code sections

    # Look for section elements
    section_elements = soup.find_all(['section', 'div'], class_=re.compile(r'section|code-section|content'))

    if not section_elements:
        # Fallback: get all text from body
        body = soup.find('body')
        if body:
            text = body.get_text(separator='\n', strip=True)
            sections.append({
                'section': None,
                'title': None,
                'content': text
            })
    else:
        for elem in section_elements:
            # Try to find section number and title
            header = elem.find(['h1', 'h2', 'h3', 'h4'])

            section_num = None
            section_title = None

            if header:
                header_text = header.get_text(strip=True)
                # Parse section number (e.g., "403.3.1.1 Outdoor Airflow Rate")
                match = re.match(r'^([\d.]+)\s+(.+)$', header_text)
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2)
                else:
                    section_title = header_text

            # Get the content text
            content = elem.get_text(separator='\n', strip=True)

            if content:
                sections.append({
                    'section': section_num,
                    'title': section_title,
                    'content': content
                })

    return sections


def clean_text(text: str) -> str:
    """Clean up extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    # Remove common boilerplate
    boilerplate = [
        'Sign up for free',
        'Create a free account',
        'UpCodes Premium',
        'Subscribe to unlock',
    ]
    for phrase in boilerplate:
        text = text.replace(phrase, '')

    return text.strip()


def scrape_code(code_slug: str, code_info: Dict) -> List[Dict[str, Any]]:
    """Scrape all chapters of a code."""
    code_name = code_info['name']
    chapters = code_info['chapters']

    all_sections = []

    print(f"\n  Scraping {code_name}...")
    print(f"  {len(chapters)} chapters to fetch")

    for chapter in chapters:
        chapter_num = chapter['num']
        chapter_slug = chapter['slug']

        print(f"    Chapter {chapter_num}: {chapter_slug}...", end=" ", flush=True)

        html = fetch_chapter(code_slug, f"{chapter_num}/{chapter_slug}")

        if html:
            sections = parse_chapter_content(html)

            for section in sections:
                section['code_name'] = code_name
                section['chapter'] = chapter_num
                section['chapter_slug'] = chapter_slug
                section['content'] = clean_text(section['content'])

            all_sections.extend(sections)
            print(f"OK ({len(sections)} sections)")
        else:
            print("FAILED")

        # Be respectful to the server
        time.sleep(1)

    return all_sections


def save_to_json(sections: List[Dict[str, Any]], output_path: Path):
    """Save scraped sections to JSON for ingestion."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)


def save_to_text(sections: List[Dict[str, Any]], output_dir: Path, code_name: str):
    """Save scraped sections as text files organized by chapter."""
    code_dir = output_dir / code_name.replace(' ', '_')
    code_dir.mkdir(parents=True, exist_ok=True)

    # Group by chapter
    chapters = {}
    for section in sections:
        chapter = section.get('chapter', 'unknown')
        if chapter not in chapters:
            chapters[chapter] = []
        chapters[chapter].append(section)

    # Save each chapter as a text file
    for chapter, chapter_sections in chapters.items():
        chapter_file = code_dir / f"chapter_{chapter}.txt"

        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(f"# {code_name} - Chapter {chapter}\n\n")

            for section in chapter_sections:
                if section.get('section'):
                    f.write(f"## Section {section['section']}")
                    if section.get('title'):
                        f.write(f": {section['title']}")
                    f.write("\n\n")

                f.write(section['content'])
                f.write("\n\n---\n\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main function to scrape all NYC codes."""
    print("=" * 60)
    print("UpCodes NYC Building Codes Scraper")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_sections = []

    for code_slug, code_info in NYC_CODES.items():
        try:
            sections = scrape_code(code_slug, code_info)
            all_sections.extend(sections)

            # Save individual code to text files
            save_to_text(sections, OUTPUT_DIR, code_info['name'])

            print(f"  -> Saved {len(sections)} sections for {code_info['name']}")

        except Exception as e:
            print(f"  ERROR scraping {code_info['name']}: {e}")
            continue

    # Save all sections to a single JSON file for ingestion
    json_path = OUTPUT_DIR / "all_codes.json"
    save_to_json(all_sections, json_path)

    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE!")
    print("=" * 60)
    print(f"\nTotal sections scraped: {len(all_sections)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"JSON file: {json_path}")
    print("\nNext step: Run ingest_scraped.py to add to database")


if __name__ == "__main__":
    main()
