"""
NYC Building Code PDF Ingestion Script
=======================================

This script:
1. Reads PDF files from the pdfs/ folder
2. Extracts text and tables using Docling
3. Splits content into chunks
4. Generates embeddings using OpenAI
5. Stores everything in PostgreSQL with pgvector

Run this script after downloading PDFs to the pdfs/ folder.
"""

import os
import sys
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

# OpenAI embedding model - this one produces 1536 dimensions
EMBEDDING_MODEL = "text-embedding-3-small"

# Chunk size configuration (from PRD)
MAX_CHUNK_TOKENS = 800  # For regular sections
MAX_TABLE_CHUNK_TOKENS = 1200  # For tables

# Database connection
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'nycbuildingcodes'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# PDF folder path
PDF_FOLDER = Path(__file__).parent.parent / 'pdfs'

# Code name mapping - maps PDF filename patterns to code names
CODE_NAME_MAPPING = {
    'BC': 'NYC Building Code 2022',
    'MC': 'NYC Mechanical Code 2022',
    'PC': 'NYC Plumbing Code 2022',
    'FC': 'NYC Fuel Gas Code 2022',
    'FireCode': 'NYC Fire Code 2022',
    'EC': 'NYC Electrical Code 2025',
    'ECC': 'NYC Energy Conservation Code 2020',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_code_name(filename: str) -> str:
    """Determine which code a PDF belongs to based on its filename."""
    for pattern, name in CODE_NAME_MAPPING.items():
        if pattern in filename:
            return name
    return "NYC Building Code 2022"  # Default


def extract_section_info(text: str) -> Dict[str, str]:
    """
    Extract section number and title from text.

    Building codes use formats like:
    - "907.2.11.1 Smoke alarms..."
    - "Section 403.3.1.1"
    - "Table 403.3.1.1"
    """
    info = {
        'section': None,
        'section_title': None,
        'parent_sections': [],
        'content_type': 'section',
        'table_name': None
    }

    # Check if this is a table
    table_match = re.match(r'^Table\s+([\d.]+)', text, re.IGNORECASE)
    if table_match:
        info['content_type'] = 'table'
        info['table_name'] = f"Table {table_match.group(1)}"
        info['section'] = table_match.group(1)
    else:
        # Look for section numbers like "907.2.11.1"
        section_match = re.match(r'^([\d]+(?:\.[\d]+)*)\s+(.+?)(?:\.|$)', text)
        if section_match:
            info['section'] = section_match.group(1)
            info['section_title'] = section_match.group(2).strip()

    # Generate parent sections
    if info['section']:
        parts = info['section'].split('.')
        for i in range(1, len(parts)):
            info['parent_sections'].append('.'.join(parts[:i]))

    return info


def estimate_tokens(text: str) -> int:
    """
    Roughly estimate token count.
    OpenAI uses ~4 characters per token on average for English text.
    """
    return len(text) // 4


def chunk_text(text: str, max_tokens: int = MAX_CHUNK_TOKENS) -> List[str]:
    """
    Split text into chunks that don't exceed max_tokens.
    Tries to split on paragraph boundaries.
    """
    if estimate_tokens(text) <= max_tokens:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        if estimate_tokens(current_chunk + para) <= max_tokens:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def process_pdf(pdf_path: Path, openai_client: OpenAI) -> List[Dict[str, Any]]:
    """
    Process a single PDF file and return a list of document chunks.
    """
    from docling.document_converter import DocumentConverter

    print(f"\n  Processing: {pdf_path.name}")

    # Initialize Docling converter
    converter = DocumentConverter()

    # Convert PDF to structured document
    result = converter.convert(str(pdf_path))

    # Get the document content as markdown (preserves structure)
    doc_content = result.document.export_to_markdown()

    # Determine which code this PDF belongs to
    code_name = get_code_name(pdf_path.name)

    # Extract chapter info from filename if possible
    chapter_match = re.search(r'Chapter\s*(\d+)', pdf_path.name, re.IGNORECASE)
    chapter = chapter_match.group(1) if chapter_match else None

    # Split into chunks
    chunks = chunk_text(doc_content)

    documents = []
    for chunk in chunks:
        # Extract section information
        section_info = extract_section_info(chunk)

        doc = {
            'content': chunk,
            'code_name': code_name,
            'chapter': chapter,
            'chapter_title': None,  # Could be extracted from content
            'section': section_info['section'],
            'section_title': section_info['section_title'],
            'parent_sections': section_info['parent_sections'],
            'content_type': section_info['content_type'],
            'table_name': section_info['table_name'],
            'table_category': None,
        }
        documents.append(doc)

    print(f"    -> Created {len(documents)} chunks")
    return documents


def generate_embeddings(texts: List[str], openai_client: OpenAI) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts using OpenAI.
    """
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def store_documents(documents: List[Dict[str, Any]], conn) -> int:
    """
    Store documents in PostgreSQL with their embeddings.
    Returns the number of documents stored.
    """
    cursor = conn.cursor()

    # Prepare data for bulk insert
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

    # Bulk insert
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


def main():
    """
    Main function to process all PDFs and store in database.
    """
    print("=" * 60)
    print("NYC Building Code Ingestion Script")
    print("=" * 60)

    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in .env file")
        sys.exit(1)

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=api_key)

    # Connect to database
    print("\nConnecting to database...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("  Connected successfully!")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)

    # Check for PDFs
    if not PDF_FOLDER.exists():
        print(f"\nERROR: PDF folder not found: {PDF_FOLDER}")
        print("Please create the folder and add PDF files.")
        sys.exit(1)

    pdf_files = list(PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print(f"\nNo PDF files found in: {PDF_FOLDER}")
        print("Please add NYC building code PDFs to this folder.")
        sys.exit(1)

    print(f"\nFound {len(pdf_files)} PDF files")

    # Process each PDF
    all_documents = []
    for pdf_path in pdf_files:
        try:
            docs = process_pdf(pdf_path, openai_client)
            all_documents.extend(docs)
        except Exception as e:
            print(f"  ERROR processing {pdf_path.name}: {e}")
            continue

    print(f"\nTotal chunks to embed: {len(all_documents)}")

    if not all_documents:
        print("No documents to process. Exiting.")
        conn.close()
        return

    # Generate embeddings in batches
    print("\nGenerating embeddings...")
    BATCH_SIZE = 100  # OpenAI allows up to 2048 per request

    for i in tqdm(range(0, len(all_documents), BATCH_SIZE)):
        batch = all_documents[i:i + BATCH_SIZE]
        texts = [doc['content'] for doc in batch]

        embeddings = generate_embeddings(texts, openai_client)

        for doc, embedding in zip(batch, embeddings):
            doc['embedding'] = embedding

    # Store in database
    print("\nStoring in database...")
    count = store_documents(all_documents, conn)
    print(f"  Stored {count} documents")

    # Close connection
    conn.close()

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nTotal documents: {count}")
    print("\nYou can now run the chatbot to query the building codes.")


if __name__ == "__main__":
    main()
