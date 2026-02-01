/**
 * Claude API Utility
 * ===================
 * Handles communication with Claude (Anthropic's AI).
 *
 * Claude receives:
 * 1. Your question
 * 2. Relevant building code sections (from vector search)
 *
 * Claude returns:
 * - An answer with citations to specific code sections
 */

import Anthropic from '@anthropic-ai/sdk';
import { SearchResult } from './db';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// The model we use
const MODEL = 'claude-sonnet-4-20250514';

/**
 * Generate a response using Claude with RAG context
 */
export async function generateResponse(
  question: string,
  relevantDocuments: SearchResult[],
  conversationHistory: Message[] = []
): Promise<string> {
  // Build the context from relevant documents
  const context = relevantDocuments
    .map((doc, i) => {
      const citation = doc.section
        ? `[${doc.code_name}, Section ${doc.section}]`
        : `[${doc.code_name}]`;

      return `--- Document ${i + 1} ${citation} ---\n${doc.content}`;
    })
    .join('\n\n');

  // Build source reference list for inline citations
  const sourceList = relevantDocuments
    .map((doc, i) => {
      const section = doc.section ? `Section ${doc.section}` : '';
      const title = doc.section_title || '';
      return `[${i + 1}] ${doc.code_name}${section ? ', ' + section : ''}${title ? ' - ' + title : ''}`;
    })
    .join('\n');

  // System prompt that instructs Claude how to respond
  const systemPrompt = `You are an expert building code consultant helping a mechanical engineer with New York City building code questions.

You have access to relevant sections from the 2022 NYC Construction Codes (Building Code, Mechanical Code, Plumbing Code, Fire Code, and Fuel Gas Code).

CITATION FORMAT - CRITICAL:
- Use inline numbered citations like [1], [2], [3] after EVERY factual statement
- Place citations IMMEDIATELY after the statement they support
- You can cite multiple sources: [1][3][5]
- Citation numbers correspond to the AVAILABLE SOURCES list below

AVAILABLE SOURCES:
${sourceList}

REQUIRED RESPONSE STRUCTURE:

1. **SUMMARY PARAGRAPH** (First)
   Write a comprehensive 2-3 sentence summary that directly answers the question with key requirements and inline citations.
   Example: "For a commercial kitchen in NYC (2022 codes), you must provide a code-compliant mechanical exhaust hood system over commercial cooking appliances [1][2]. You must also supply appropriately balanced makeup air and coordinate with required automatic fire-suppression systems [3][4]."

2. **DETAILED REQUIREMENTS BY TOPIC**
   Organize the rest of your answer into clear sections with headers. For a commercial kitchen question, use sections like:

   **General ventilation basis**
   - Bullet points with specific requirements and citations [X]

   **Exhaust hoods and ducts**
   - Bullet points with specific section references [X]

   **Fire protection requirements**
   - Bullet points with requirements from Fire Code [X]

   **Makeup air and air balance**
   - Bullet points with airflow requirements [X]

WRITING RULES:
- Include SPECIFIC section numbers (e.g., "per NYC Mechanical Code Section 507.2" or "Section 506 of the Mechanical Code")
- Include SPECIFIC measurements when available (CFM, feet, percentages)
- Cross-reference between codes when relevant (e.g., "which also requires compliance with Fire Code Section 609")
- Be COMPREHENSIVE - cover all relevant aspects from the context
- Do NOT make up requirements not in the context
- Do NOT include citations for information not in the provided documents

CONTEXT FROM NYC BUILDING CODES:
${context}

Generate a comprehensive, well-organized response with proper inline citations.`;

  // Build message history
  const messages: Anthropic.MessageParam[] = [
    ...conversationHistory.map((msg) => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
    })),
    {
      role: 'user',
      content: question,
    },
  ];

  // Call Claude API
  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 4096,
    system: systemPrompt,
    messages,
  });

  // Extract text from response
  const textBlock = response.content.find((block) => block.type === 'text');
  return textBlock ? textBlock.text : 'No response generated.';
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}
