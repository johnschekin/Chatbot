# Product Requirements Document: NYC Building Code Chatbot

## Overview

A local RAG (Retrieval-Augmented Generation) chatbot that enables a mechanical engineer to query New York City building code documents using natural language. The system ingests official NYC code PDFs and provides accurate answers with citations.

---

## Key Concepts Explained (Beginner's Guide)

This section explains the technical terms used throughout this document in simple language.

### What is an LLM?

**LLM (Large Language Model)** is an AI that understands and generates human language. Think of it like a very smart assistant that has read millions of books and documents. Claude (made by Anthropic) is the LLM we'll use.

**Analogy**: If you asked a librarian who has memorized every book in the library a question, they could give you an answer. An LLM is like that librarian, but digital.

### What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that makes LLMs smarter by giving them access to specific documents.

**The Problem**: Claude is smart, but it doesn't know the specific NYC building codes. If you ask "What's the ventilation rate for a classroom?", Claude might give a general answer, but not the exact NYC code requirement.

**The Solution (RAG)**:
1. We store all the NYC building codes in a searchable database
2. When you ask a question, we first SEARCH the database for relevant sections
3. We give those sections to Claude along with your question
4. Claude reads them and gives you an accurate answer WITH citations

**Analogy**: Instead of asking someone to answer from memory, you hand them the relevant pages from a textbook and say "answer based on this."

```
YOUR QUESTION ──────────────────────────────────────────────────┐
       │                                                        │
       ▼                                                        ▼
┌─────────────────┐    relevant sections    ┌─────────────────────┐
│  Search the     │ ────────────────────►   │  Claude reads them  │
│  building codes │                         │  and answers you    │
└─────────────────┘                         └─────────────────────┘
```

### What are Embeddings?

**Embeddings** turn text into numbers so computers can understand similarity.

**The Problem**: Computers don't understand that "ventilation requirements" and "air flow rates" are related concepts. To a computer, they're just different letters.

**The Solution**: Embeddings convert text into a list of numbers (called a "vector"). Similar meanings get similar numbers.

**Example**:
- "kitchen ventilation" → [0.2, 0.8, 0.5, 0.1, ...]
- "cooking area airflow" → [0.21, 0.79, 0.52, 0.09, ...] (very similar numbers!)
- "plumbing pipes" → [0.9, 0.1, 0.3, 0.7, ...] (very different numbers)

**Analogy**: It's like GPS coordinates. "NYC" and "Manhattan" have similar coordinates because they're close together. "NYC" and "Tokyo" have very different coordinates.

### What is a Vector Database?

**Vector Database** stores embeddings and lets you search for similar content.

**How it works**:
1. Every section of the building code gets converted to embeddings (numbers)
2. These are stored in the vector database (PostgreSQL with pgvector)
3. When you ask a question, your question is also converted to numbers
4. The database finds sections with similar numbers = relevant content

**Analogy**: It's like a smart filing cabinet that can find "documents about kitchen ventilation" even if you search for "cooking area air requirements" because it understands they mean similar things.

### What is Chunking?

**Chunking** means breaking large documents into smaller pieces.

**The Problem**: The NYC Building Code is 3,000+ pages. We can't search the whole thing at once or give it all to Claude.

**The Solution**: We break it into small "chunks" (pieces), each containing one section of the code. Each chunk is stored separately with information about where it came from.

**Example**:
```
CHUNK 1: Section 907.2.11.1 - Smoke alarms shall be installed...
         (from: Building Code, Chapter 9, Fire Protection)

CHUNK 2: Section 403.3.1.1 - Ventilation systems shall provide...
         (from: Mechanical Code, Chapter 4, Ventilation)
```

### What is Docling?

**Docling** is a tool (made by IBM) that reads PDF files and extracts the text, including tables.

**Why we need it**: Building codes have complex formatting - tables, numbered sections, cross-references. Docling is good at preserving this structure when extracting text.

### What is pgvector?

**pgvector** is an add-on for PostgreSQL (a database) that lets it store and search embeddings.

**Why we use it**: PostgreSQL is a reliable, well-known database. Adding pgvector gives it the ability to do the "similarity search" we need for RAG.

### What is Next.js?

**Next.js** is a framework for building websites and web applications using JavaScript.

**Why we use it**: It lets us build the chat interface you'll use to ask questions. It runs locally on your computer (no internet hosting needed).

### How It All Works Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ONE-TIME SETUP (Ingestion)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   NYC Building     Docling extracts      Chunks get          Stored in │
│   Code PDFs    ──► text & tables    ──►  embeddings     ──►  Database  │
│                                          (numbers)          (pgvector) │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      EVERY TIME YOU ASK A QUESTION                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. You type: "What are ventilation requirements for a commercial       │
│               kitchen?"                                                 │
│                                                                         │
│  2. Your question gets converted to embeddings (numbers)                │
│                                                                         │
│  3. Database finds chunks with similar numbers                          │
│     → Returns: Section 403.3.1.1, Table 403.3.1.1, etc.                │
│                                                                         │
│  4. Claude receives: Your question + relevant code sections             │
│                                                                         │
│  5. Claude responds: "Per NYC Mechanical Code Section 403.3.1.1,        │
│                       commercial kitchens require..."                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Glossary Quick Reference

| Term | Simple Definition |
|------|-------------------|
| **LLM** | AI that understands and writes human language (like Claude) |
| **RAG** | Technique to give an LLM access to your specific documents |
| **Embeddings** | Converting text to numbers so computers can find similar content |
| **Vector** | A list of numbers representing text meaning |
| **Vector Database** | Database that can search for similar meanings |
| **Chunk** | A small piece of a larger document |
| **pgvector** | PostgreSQL add-on for storing/searching embeddings |
| **Docling** | Tool to extract text and tables from PDFs |
| **Next.js** | Framework for building the web interface |
| **API** | Way for programs to talk to each other (like calling Claude) |
| **Local** | Runs on your computer, not on the internet |

---

## 1. Problem Statement

Navigating NYC building codes is time-consuming and complex. Codes span thousands of pages across multiple documents (Building, Mechanical, Plumbing, Fire, Electrical, Energy Conservation, Fuel Gas). A mechanical engineer needs quick, accurate answers with proper citations to code sections.

---

## 2. Target User

| Attribute | Value |
|-----------|-------|
| User Type | Single user (sole operator) |
| Role | Mechanical Engineer |
| Location | New York City |
| Technical Level | Power user |

---

## 3. Goals

1. Provide accurate answers to NYC building code questions
2. Return exact citations with section numbers
3. Support complex queries spanning tables and cross-references
4. Enable session-based conversations with memory
5. Allow saving and revisiting past queries
6. Export answers as reports or files

---

## 4. Document Scope

### 4.1 Included Codes (Current Versions Only)

| Code | Source | Chapters/Scope |
|------|--------|----------------|
| NYC Building Code 2022 | NYC.gov | 35 chapters + 18 appendices |
| NYC Mechanical Code 2022 | NYC.gov | 15 chapters + 3 appendices |
| NYC Plumbing Code 2022 | NYC.gov | 15 chapters + 5 appendices |
| NYC Fuel Gas Code 2022 | NYC.gov | 8 chapters + 7 appendices |
| NYC Fire Code 2022 | NYC.gov (FDNY) | Full code |
| NYC Electrical Code 2025 | NYC.gov | Full code (NFPA 70 based) |
| NYC Energy Conservation Code 2020 | NYC.gov | Full code |
| General Administrative Provisions | NYC.gov | 5 chapters (Title 28) |

### 4.2 Document Format
- Source: PDF files from NYC.gov
- Estimated Volume: ~3,000-4,000+ pages total

### 4.3 Exclusions
- Historical/superseded code versions
- Non-NYC codes (NYS codes, ICC base codes without NYC amendments)

---

## 5. Functional Requirements

### 5.1 Document Ingestion

| ID | Requirement | Priority |
|----|-------------|----------|
| F-ING-01 | Ingest PDF documents from NYC.gov | Must Have |
| F-ING-02 | Extract structured data from tables | Must Have |
| F-ING-03 | Preserve cross-references between code sections | Must Have |
| F-ING-04 | Support manual re-ingestion when codes update | Must Have |
| F-ING-05 | Chunk documents appropriately for RAG retrieval | Must Have |

### 5.2 Query & Response

| ID | Requirement | Priority |
|----|-------------|----------|
| F-QRY-01 | Accept natural language questions | Must Have |
| F-QRY-02 | Return answers with exact section citations | Must Have |
| F-QRY-03 | Provide summaries alongside citations | Must Have |
| F-QRY-04 | Handle queries across multiple code documents | Must Have |
| F-QRY-05 | Support table-based lookups | Must Have |

### 5.3 Conversation Management

| ID | Requirement | Priority |
|----|-------------|----------|
| F-CONV-01 | Maintain context within a session | Must Have |
| F-CONV-02 | Support follow-up questions | Must Have |
| F-CONV-03 | Save query history persistently | Must Have |
| F-CONV-04 | Allow revisiting past queries | Must Have |
| F-CONV-05 | Support multiple chat sessions | Should Have |

### 5.4 Export & Reporting

| ID | Requirement | Priority |
|----|-------------|----------|
| F-EXP-01 | Export individual answers to file | Must Have |
| F-EXP-02 | Generate reports from conversations | Must Have |
| F-EXP-03 | Include citations in exports | Must Have |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NF-PERF-01 | Query response time | < 30 seconds |
| NF-PERF-02 | Document ingestion | One-time process, no time constraint |

### 6.2 Security & Access

| ID | Requirement | Notes |
|----|-------------|-------|
| NF-SEC-01 | Authentication | Not required (single user) |
| NF-SEC-02 | Authorization | Not required (single user) |
| NF-SEC-03 | Data encryption | Not required (local deployment) |

### 6.3 Deployment

| ID | Requirement | Value |
|----|-------------|-------|
| NF-DEP-01 | Deployment model | Local only |
| NF-DEP-02 | Internet required | Yes (Claude API calls) |
| NF-DEP-03 | Offline mode | Not required |

### 6.4 Constraints

| ID | Constraint | Notes |
|----|------------|-------|
| NF-CON-01 | Cost constraints | None |
| NF-CON-02 | Storage constraints | None |

---

## 7. Technical Architecture

### 7.1 Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js (Local Web UI) |
| Backend | Next.js API Routes or Node.js |
| LLM | Claude API (Anthropic) |
| Vector Database | PostgreSQL with pgvector (local) |
| Embeddings | OpenAI Embeddings API |
| PDF Processing | Docling (IBM) |
| Table Extraction | Docling (IBM) |
| Export Format | Markdown |

### 7.2 High-Level Architecture

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|   Next.js Web    |---->|   RAG Backend    |---->|   Claude API     |
|   Interface      |     |   (Retrieval)    |     |   (Generation)   |
|                  |     |                  |     |                  |
+------------------+     +--------+---------+     +------------------+
                                 |
                                 v
                         +-------+--------+
                         |                |
                         | Vector Store   |
                         | (Embeddings)   |
                         |                |
                         +----------------+
                                 ^
                                 |
                         +-------+--------+
                         |                |
                         | PDF Ingestion  |
                         | Pipeline       |
                         |                |
                         +----------------+
```

### 7.3 Data Flow

1. **Ingestion Pipeline**
   - Download PDFs from NYC.gov
   - Extract text and tables from PDFs
   - Preserve structure and cross-references
   - Chunk content appropriately
   - Generate embeddings
   - Store in vector database

2. **Query Pipeline**
   - User submits natural language query
   - Generate query embedding
   - Retrieve relevant chunks from vector store
   - Construct prompt with context and citations
   - Send to Claude API
   - Return response with section citations

3. **Session Management**
   - Store conversation history per session
   - Persist query history to database/file
   - Enable session recall and export

### 7.4 Chunking Strategy

Based on analysis of actual NYC building code documents from NYC.gov:

#### Document Structure Observations
- **Section numbering**: Hierarchical format (e.g., `907.2.11.1`)
- **Typical section length**: 50-200 words (2-4 sentences)
- **Tables**: Large tables like Table 403.3.1.1 contain 68 rows grouped by category
- **Cross-references**: Frequent references between sections (e.g., "in accordance with Section 907.6.5")

#### Chunk Size Configuration

| Content Type | Chunk Size | Overlap | Rationale |
|--------------|------------|---------|-----------|
| Code Sections | 500-800 tokens | 100 tokens | Natural unit; keeps full section + parent context |
| Tables | 800-1200 tokens | 100 tokens | Keep headers + chunk by category group |

#### Chunking Approach: Section-Based

Each chunk includes:
- Full section content
- Hierarchical metadata for context and citation

#### Chunk Schema

```json
{
  "content": "907.2.11.1 Single- or multiple-station smoke alarms shall be installed...",
  "metadata": {
    "code": "NYC Building Code 2022",
    "chapter": "9",
    "chapter_title": "Fire Protection Systems",
    "section": "907.2.11.1",
    "section_title": "Smoke Alarms in Groups R-2 and R-3",
    "parent_sections": ["907", "907.2", "907.2.11"],
    "content_type": "section",
    "has_table": false
  }
}
```

#### Table Chunking

```json
{
  "content": "Table 403.3.1.1 Minimum Ventilation Rates\n[Headers: Occupancy Classification | Occupant Density | Outdoor Airflow Rate...]\n\nEducation:\n- Auditoriums: 150 | 0.06 | 7.5...\n- Classrooms: 35 | 0.12 | 10...",
  "metadata": {
    "code": "NYC Mechanical Code 2022",
    "chapter": "4",
    "section": "403.3.1.1",
    "content_type": "table",
    "table_name": "Table 403.3.1.1",
    "table_category": "Education",
    "total_categories": 16,
    "has_table": true
  }
}
```

#### Large Table Strategy
- Split by category group (e.g., "Education", "Office", "Retail")
- Always include column headers in each chunk
- Store full table separately for exact lookups when needed

---

## 8. User Interface Requirements

### 8.1 Main Chat Interface

- Text input for queries
- Response display with markdown formatting
- Citation display with section numbers
- Code highlighting where applicable
- Copy response functionality

### 8.2 Session Management

- New chat button
- Session history sidebar
- Session search/filter
- Delete session option

### 8.3 Export Features

- Export current answer button
- Export full conversation button
- Format: Markdown (.md)

### 8.4 Query History

- Searchable history of past queries
- Quick re-run past queries
- Favorite/bookmark queries

---

## 9. Sample Queries

The system should handle queries such as:

1. "What are the ventilation requirements for a commercial kitchen in New York City?"
2. "What are the requirements for a fire alarm system for a student dormitory?"
3. "What is the minimum duct clearance for a mechanical room?"
4. "What are the smoke damper requirements per the fire code?"
5. "What does Section 28-101.1 say?"

---

## 10. Success Criteria

| Metric | Target |
|--------|--------|
| Citation accuracy | Correct section numbers in 95%+ of responses |
| Query comprehension | Relevant answers for 90%+ of well-formed queries |
| Table data retrieval | Accurate table lookups for 85%+ of table-based queries |
| Response time | < 30 seconds for standard queries |

---

## 11. Out of Scope

- Multi-user support
- Authentication/authorization
- Automatic code update detection
- Historical code version queries
- Comparison across code sections
- Mobile application
- Cloud deployment

---

## 12. Future Considerations

These items are explicitly out of scope but may be considered later:

- Integration with project management tools
- Automatic code update notifications
- Support for other jurisdictions (NYS, NJ, etc.)
- Drawing/diagram analysis
- Code change tracking between versions

---

## 13. Resolved Decisions

| Decision | Choice |
|----------|--------|
| Vector Database | PostgreSQL with pgvector (local) |
| Embedding Model | OpenAI Embeddings API |
| Export Format | Markdown |
| PDF Processing & Table Extraction | Docling (IBM) |
| Chunking Strategy | Section-based, 500-800 tokens (sections), 800-1200 tokens (tables) |

---

## 14. References

- [NYC Buildings Codes](https://www.nyc.gov/site/buildings/codes/nyc-code.page)
- [2022 Construction Codes](https://www.nyc.gov/site/buildings/codes/2022-construction-codes.page)
- [NYC Fire Code](https://www.nyc.gov/site/fdny/codes/fire-code/fire-code.page)
- [NYC Electrical Code](https://www.nyc.gov/site/buildings/codes/electrical-code.page)
- [NYC Energy Conservation Code](https://www.nyc.gov/site/buildings/codes/2020-energy-conservation-code.page)

---

*Document Version: 1.0*
*Created: January 31, 2026*
