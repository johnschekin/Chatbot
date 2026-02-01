/**
 * Embeddings Utility
 * ==================
 * Generates embeddings using OpenAI API.
 *
 * What are embeddings?
 * - Numbers that represent the meaning of text
 * - Similar meanings = similar numbers
 * - Used to find relevant documents for your question
 */

import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// The model we use - produces 1536 dimensions
const EMBEDDING_MODEL = 'text-embedding-3-small';

/**
 * Generate an embedding for a single text
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: text,
  });

  return response.data[0].embedding;
}
