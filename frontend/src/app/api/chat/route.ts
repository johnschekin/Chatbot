/**
 * Chat API Route
 * ===============
 * This is the main API endpoint for the chatbot.
 *
 * How it works:
 * 1. Receives your question
 * 2. Converts question to embedding (numbers)
 * 3. Searches database for similar building code sections
 * 4. Sends question + relevant sections to Claude
 * 5. Returns Claude's answer with citations
 */

import { NextRequest, NextResponse } from 'next/server';
import { generateEmbedding } from '@/lib/embeddings';
import { searchWithExpansion } from '@/lib/db';
import { generateResponse, Message } from '@/lib/claude';

// How many relevant documents to retrieve (more = better answers but slower)
const NUM_DOCUMENTS = 20;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { question, history = [] } = body as {
      question: string;
      history?: Message[];
    };

    if (!question || typeof question !== 'string') {
      return NextResponse.json(
        { error: 'Question is required' },
        { status: 400 }
      );
    }

    console.log(`\n[Chat API] Question: "${question.substring(0, 50)}..."`);

    // Step 1: Generate embedding for the question
    console.log('[Chat API] Generating embedding...');
    const queryEmbedding = await generateEmbedding(question);

    // Step 2: Search for relevant documents using hybrid search + query expansion
    console.log('[Chat API] Searching documents (hybrid search)...');
    const relevantDocs = await searchWithExpansion(queryEmbedding, question, NUM_DOCUMENTS);
    console.log(`[Chat API] Found ${relevantDocs.length} relevant documents`);

    // Log which documents were found (for debugging)
    relevantDocs.forEach((doc, i) => {
      const similarity = typeof doc.similarity === 'number' ? doc.similarity : parseFloat(doc.similarity) || 0;
      console.log(
        `  ${i + 1}. ${doc.code_name} ${doc.section || '(no section)'} (score: ${similarity.toFixed(4)})`
      );
    });

    // Step 3: Generate response using Claude
    console.log('[Chat API] Calling Claude...');
    const answer = await generateResponse(question, relevantDocs, history);

    // Step 4: Return the response with full content for quotes
    return NextResponse.json({
      answer,
      sources: relevantDocs.map((doc) => ({
        id: doc.id,
        code_name: doc.code_name,
        section: doc.section,
        section_title: doc.section_title,
        content: doc.content, // Include full content for displaying quotes
        similarity: typeof doc.similarity === 'number' ? doc.similarity : parseFloat(doc.similarity) || 0,
      })),
    });
  } catch (error) {
    console.error('[Chat API] Error:', error);

    return NextResponse.json(
      {
        error: 'Failed to process question',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
