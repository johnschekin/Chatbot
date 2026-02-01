/**
 * Database Connection
 * ===================
 * Handles PostgreSQL connection for the chatbot.
 * Implements hybrid search (vector + keyword) for better results.
 */

import { Pool } from 'pg';

// Create a connection pool (reuses connections for efficiency)
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'nycbuildingcodes',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
});

export default pool;

/**
 * Hybrid Search: Combines vector similarity with keyword matching
 * This produces much better results than vector-only search
 */
export async function searchDocuments(
  queryEmbedding: number[],
  limit: number = 15,
  query?: string
): Promise<SearchResult[]> {
  const client = await pool.connect();

  try {
    const embeddingStr = `[${queryEmbedding.join(',')}]`;

    if (query) {
      // HYBRID SEARCH: Combine vector similarity with keyword matching
      // Uses Reciprocal Rank Fusion (RRF) to merge results from both methods

      // Extract important keywords from query for keyword search
      const keywords = extractKeywords(query);
      const keywordPattern = keywords.join(' | '); // PostgreSQL tsquery OR pattern

      const result = await client.query(`
        WITH vector_search AS (
          SELECT
            id,
            content,
            code_name,
            chapter,
            chapter_title,
            section,
            section_title,
            content_type,
            table_name,
            1 - (embedding <=> $1::vector) as vector_score,
            ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) as vector_rank
          FROM documents
          ORDER BY embedding <=> $1::vector
          LIMIT 50
        ),
        keyword_search AS (
          SELECT
            id,
            content,
            code_name,
            chapter,
            chapter_title,
            section,
            section_title,
            content_type,
            table_name,
            ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', $3)) as keyword_score,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', $3)) DESC) as keyword_rank
          FROM documents
          WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $3)
          ORDER BY keyword_score DESC
          LIMIT 50
        ),
        combined AS (
          SELECT
            COALESCE(v.id, k.id) as id,
            COALESCE(v.content, k.content) as content,
            COALESCE(v.code_name, k.code_name) as code_name,
            COALESCE(v.chapter, k.chapter) as chapter,
            COALESCE(v.chapter_title, k.chapter_title) as chapter_title,
            COALESCE(v.section, k.section) as section,
            COALESCE(v.section_title, k.section_title) as section_title,
            COALESCE(v.content_type, k.content_type) as content_type,
            COALESCE(v.table_name, k.table_name) as table_name,
            COALESCE(v.vector_score, 0) as vector_score,
            COALESCE(k.keyword_score, 0) as keyword_score,
            -- RRF scoring: 1/(k+rank) for each method, then sum
            -- k=60 is a common constant that works well
            (COALESCE(1.0 / (60 + v.vector_rank), 0) + COALESCE(1.0 / (60 + k.keyword_rank), 0)) as rrf_score
          FROM vector_search v
          FULL OUTER JOIN keyword_search k ON v.id = k.id
        )
        SELECT
          id,
          content,
          code_name,
          chapter,
          chapter_title,
          section,
          section_title,
          content_type,
          table_name,
          -- Use RRF score as similarity for ranking
          rrf_score as similarity,
          vector_score,
          keyword_score
        FROM combined
        ORDER BY rrf_score DESC
        LIMIT $2
      `, [embeddingStr, limit, query]);

      return result.rows;
    } else {
      // Fallback to vector-only search if no query provided
      const result = await client.query(`
        SELECT
          id,
          content,
          code_name,
          chapter,
          chapter_title,
          section,
          section_title,
          content_type,
          table_name,
          1 - (embedding <=> $1::vector) as similarity
        FROM documents
        ORDER BY embedding <=> $1::vector
        LIMIT $2
      `, [embeddingStr, limit]);

      return result.rows;
    }
  } finally {
    client.release();
  }
}

/**
 * Extract important keywords from a query for keyword search
 */
function extractKeywords(query: string): string[] {
  // Remove common stop words and keep important terms
  const stopWords = new Set([
    'what', 'are', 'the', 'for', 'a', 'an', 'in', 'of', 'to', 'and', 'or',
    'is', 'it', 'this', 'that', 'with', 'as', 'be', 'on', 'at', 'by',
    'how', 'do', 'does', 'can', 'which', 'where', 'when', 'who', 'why',
    'requirements', 'requirement', 'need', 'needs', 'should', 'must'
  ]);

  return query
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.has(word));
}

/**
 * Search with query expansion - adds related terms to improve recall
 */
export async function searchWithExpansion(
  queryEmbedding: number[],
  query: string,
  limit: number = 20
): Promise<SearchResult[]> {
  // Expand query with related building code terms
  const expansions: Record<string, string[]> = {
    'kitchen': ['commercial kitchen', 'cooking', 'food preparation', 'hood', 'exhaust'],
    'ventilation': ['exhaust', 'makeup air', 'airflow', 'cfm', 'hvac', 'duct'],
    'fire': ['fire alarm', 'fire protection', 'sprinkler', 'smoke', 'suppression'],
    'alarm': ['fire alarm', 'smoke detector', 'notification', 'alert'],
    'dormitory': ['residential', 'sleeping', 'occupancy', 'R-2', 'dwelling'],
    'commercial': ['business', 'mercantile', 'assembly', 'occupancy'],
    'exhaust': ['ventilation', 'duct', 'hood', 'airflow', 'cfm'],
    'sprinkler': ['fire protection', 'suppression', 'nfpa', 'standpipe'],
  };

  // Build expanded query
  const words = query.toLowerCase().split(/\s+/);
  const expandedTerms: string[] = [...words];

  for (const word of words) {
    if (expansions[word]) {
      expandedTerms.push(...expansions[word]);
    }
  }

  const expandedQuery = [...new Set(expandedTerms)].join(' ');

  return searchDocuments(queryEmbedding, limit, expandedQuery);
}

export interface SearchResult {
  id: number;
  content: string;
  code_name: string;
  chapter: string | null;
  chapter_title: string | null;
  section: string | null;
  section_title: string | null;
  content_type: string;
  table_name: string | null;
  similarity: number;
}
