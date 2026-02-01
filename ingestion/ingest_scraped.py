"""
Ingest Scraped NYC Building Codes
==================================

This script:
1. Reads the scraped JSON file from UpCodes
2. Chunks the content appropriately
3. Generates embeddings using OpenAI
4. Stores everything in PostgreSQL with pgvector

Run this after running scrape_upcodes.py
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

# Add parent directory to path to find .env file
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / '.env')

# =============================================================================
# CONFIGURATION
# =============================================================================

# OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-3-small"

# Chunk size configuration
MAX_CHUNK_CHARS = 2000  # ~500 tokens
MIN_CHUNK_CHARS = 100   # Skip very small chunks

# Database connection
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'nycbuildingcodes'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Scraped data path
SCRAPED_JSON = Path(__file__).parent / "scraped_codes" / "all_codes.json"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def chunk_content(content: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """
    Split content into chunks that don't exceed max_chars.
    Tries to split on paragraph or sentence boundaries.
    """
    if len(content) <= max_chars:
        return [content]

    chunks = []

    # First try to split on double newlines (paragraphs)
    paragraphs = content.split('\n\n')

    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If paragraph itself is too long, split on sentences
            if len(para) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_chars:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
            else:
                current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def extract_section_number(text: str) -> tuple:
    """Extract section number and title from text."""
    # Look for patterns like "403.3.1.1" at the start
    match = re.match(r'^([\d]+(?:\.[\d]+)*)\s*(.*)$', text[:200])
    if match:
        return match.group(1), match.group(2).strip()
    return None, None


def generate_embeddings_batch(texts: List[str], client: OpenAI) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def clear_old_data(conn):
    """Clear existing data from the documents table."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents")
    conn.commit()
    cursor.close()
    print("  Cleared existing documents from database")


def store_documents(documents: List[Dict[str, Any]], conn) -> int:
    """Store documents in PostgreSQL with their embeddings."""
    cursor = conn.cursor()

    values = []
    for doc in documents:
        values.append((
            doc['content'],
            doc['code_name'],
            doc.get('chapter'),
            doc.get('chapter_title'),
            doc.get('section'),
            doc.get('section_title'),
            doc.get('parent_sections', []),
            doc.get('content_type', 'section'),
            doc.get('table_name'),
            doc.get('table_category'),
            doc['embedding']
        ))

    insert_query = """
        INSERT INTO documents (
            content, code_name, chapter, chapter_title, section,
            section_title, parent_sections, content_type, table_name,
            table_category, embedding
        ) VALUES %s
    """

    execute_values(
        cursor,
        insert_query,
        values,
        template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)"
    )

    conn.commit()
    cursor.close()

    return len(values)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main ingestion function."""
    print("=" * 60)
    print("NYC Building Codes Ingestion (from scraped data)")
    print("=" * 60)

    # Check for files and API key
    if not SCRAPED_JSON.exists():
        print(f"ERROR: Scraped data not found at {SCRAPED_JSON}")
        print("Run scrape_upcodes.py first")
        sys.exit(1)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in .env file")
        sys.exit(1)

    # Initialize clients
    openai_client = OpenAI(api_key=api_key)

    print("\nConnecting to database...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("  Connected successfully!")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)

    # Clear old data
    print("\nClearing old data...")
    clear_old_data(conn)

    # Load scraped data
    print(f"\nLoading scraped data from {SCRAPED_JSON}...")
    with open(SCRAPED_JSON, 'r', encoding='utf-8') as f:
        scraped_sections = json.load(f)
    print(f"  Loaded {len(scraped_sections)} sections")

    # Process sections into document chunks
    print("\nProcessing sections into chunks...")
    all_documents = []

    for section in tqdm(scraped_sections, desc="  Processing"):
        content = section.get('content', '')

        # Skip very small content
        if len(content) < MIN_CHUNK_CHARS:
            continue

        # Chunk the content
        chunks = chunk_content(content)

        for chunk in chunks:
            # Try to extract section number from content
            section_num = section.get('section')
            section_title = section.get('title')

            if not section_num:
                section_num, extracted_title = extract_section_number(chunk)
                if extracted_title and not section_title:
                    section_title = extracted_title

            # Detect if this is a table
            content_type = 'section'
            table_name = None
            if 'TABLE' in chunk.upper()[:50] or re.match(r'^Table\s+[\d.]+', chunk):
                content_type = 'table'
                table_match = re.match(r'^Table\s+([\d.]+)', chunk)
                if table_match:
                    table_name = f"Table {table_match.group(1)}"

            doc = {
                'content': chunk,
                'code_name': section.get('code_name', 'NYC Building Code 2022'),
                'chapter': section.get('chapter'),
                'chapter_title': section.get('chapter_slug', '').replace('-', ' ').title(),
                'section': section_num,
                'section_title': section_title,
                'parent_sections': [],
                'content_type': content_type,
                'table_name': table_name,
                'table_category': None,
            }
            all_documents.append(doc)

    print(f"  Created {len(all_documents)} document chunks")

    # Generate embeddings in batches
    print("\nGenerating embeddings (this may take a while)...")
    BATCH_SIZE = 100

    for i in tqdm(range(0, len(all_documents), BATCH_SIZE), desc="  Embedding"):
        batch = all_documents[i:i + BATCH_SIZE]
        texts = [doc['content'] for doc in batch]

        try:
            embeddings = generate_embeddings_batch(texts, openai_client)
            for doc, embedding in zip(batch, embeddings):
                doc['embedding'] = embedding
        except Exception as e:
            print(f"\n  ERROR generating embeddings for batch {i}: {e}")
            # Skip this batch
            for doc in batch:
                doc['embedding'] = None

    # Filter out documents without embeddings
    all_documents = [doc for doc in all_documents if doc.get('embedding')]
    print(f"\n  Documents with embeddings: {len(all_documents)}")

    # Store in database in batches
    print("\nStoring in database...")
    STORE_BATCH_SIZE = 500
    total_stored = 0

    for i in tqdm(range(0, len(all_documents), STORE_BATCH_SIZE), desc="  Storing"):
        batch = all_documents[i:i + STORE_BATCH_SIZE]
        try:
            count = store_documents(batch, conn)
            total_stored += count
        except Exception as e:
            print(f"\n  ERROR storing batch {i}: {e}")
            conn.rollback()

    conn.close()

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nTotal documents stored: {total_stored}")
    print("\nYou can now test the chatbot at http://localhost:3000")


if __name__ == "__main__":
    main()
