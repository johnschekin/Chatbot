'use client';

/**
 * NYC Building Code Chatbot
 * =========================
 * Main chat interface for querying building codes.
 * Features inline citations with hover tooltips and clickable source quotes.
 */

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

// Types for our chat
interface Source {
  id: number;
  code_name: string;
  section: string | null;
  section_title: string | null;
  content: string;
  similarity: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

/**
 * Format code name to shorter version like UpCodes
 * "NYC Mechanical Code 2022" -> "NYC MC"
 */
function formatCodeName(codeName: string): string {
  const mapping: Record<string, string> = {
    'NYC Mechanical Code 2022': 'NYC MC',
    'NYC Building Code 2022': 'NYC BC',
    'NYC Fire Code 2022': 'NYC FC',
    'NYC Plumbing Code 2022': 'NYC PC',
    'NYC Fuel Gas Code 2022': 'NYC FGC',
  };
  return mapping[codeName] || codeName;
}

/**
 * Citation Tooltip Component
 * Shows source details on hover, full quote on click
 */
function CitationTooltip({
  number,
  source,
  onSelect,
  isSelected,
}: {
  number: number;
  source: Source | undefined;
  onSelect: (source: Source | null) => void;
  isSelected: boolean;
}) {
  const [showTooltip, setShowTooltip] = useState(false);

  if (!source) {
    return <span className="text-green-700 font-medium">[{number}]</span>;
  }

  const shortName = formatCodeName(source.code_name);
  const sectionRef = source.section ? ` ${source.section}` : '';

  return (
    <span className="relative inline-block">
      <span
        className={`font-medium cursor-pointer hover:underline ${
          isSelected ? 'text-green-800 bg-green-100 px-1 rounded' : 'text-green-700 hover:text-green-800'
        }`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => onSelect(isSelected ? null : source)}
      >
        [{number}]
      </span>
      {showTooltip && !isSelected && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50 pointer-events-none">
          <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
            <span className="font-semibold text-green-300">{shortName}{sectionRef}</span>
            {source.section_title && (
              <span className="text-gray-300 ml-1">{source.section_title}</span>
            )}
            <div className="text-gray-400 text-xs mt-1">Click to view quote</div>
          </div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
      )}
    </span>
  );
}

/**
 * Source Quote Panel - Shows the full code quote
 */
function SourceQuotePanel({
  source,
  onClose,
}: {
  source: Source;
  onClose: () => void;
}) {
  const shortName = formatCodeName(source.code_name);
  const sectionRef = source.section ? ` ${source.section}` : '';

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h4 className="font-semibold text-green-800">
            {shortName}{sectionRef}
            {source.section_title && ` ${source.section_title}`}
          </h4>
          <p className="text-xs text-green-700">{source.code_name}</p>
        </div>
        <button
          onClick={onClose}
          className="text-green-400 hover:text-green-700 text-xl leading-none"
        >
          ×
        </button>
      </div>
      <div className="bg-white rounded border border-green-100 p-3 text-sm text-gray-700 max-h-48 overflow-y-auto">
        {source.content}
      </div>
    </div>
  );
}

/**
 * Process children recursively to replace citation patterns with interactive tooltips
 */
function processChildren(
  children: React.ReactNode,
  sources: Source[] | undefined,
  selectedSource: Source | null,
  onSelectSource: (source: Source | null) => void
): React.ReactNode {
  if (typeof children === 'string') {
    const parts = children.split(/(\[\d+\])/g);
    return parts.map((part, index) => {
      const citationMatch = part.match(/^\[(\d+)\]$/);
      if (citationMatch) {
        const num = parseInt(citationMatch[1], 10);
        const source = sources?.[num - 1];
        return (
          <CitationTooltip
            key={index}
            number={num}
            source={source}
            onSelect={onSelectSource}
            isSelected={selectedSource?.id === source?.id}
          />
        );
      }
      return part;
    });
  }

  if (Array.isArray(children)) {
    return children.map((child, index) => (
      <span key={index}>
        {processChildren(child, sources, selectedSource, onSelectSource)}
      </span>
    ));
  }

  return children;
}

/**
 * Render message content with markdown and interactive citations
 */
function MessageContent({
  content,
  sources,
  selectedSource,
  onSelectSource,
}: {
  content: string;
  sources?: Source[];
  selectedSource: Source | null;
  onSelectSource: (source: Source | null) => void;
}) {
  const process = (children: React.ReactNode) =>
    processChildren(children, sources, selectedSource, onSelectSource);

  return (
    <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-800 prose-strong:text-gray-800 prose-li:text-gray-800">
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <p className="mb-2 last:mb-0">{process(children)}</p>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold mt-4 mb-2 text-gray-800">{process(children)}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-bold mt-3 mb-2 text-gray-800">{process(children)}</h3>
          ),
          strong: ({ children }) => (
            <strong className="font-bold">{process(children)}</strong>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-2">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-2">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="mb-1">{process(children)}</li>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default function Home() {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Clear selected source when sending new message
  const handleSelectSource = (source: Source | null) => {
    setSelectedSource(source);
  };

  // Send a message
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    setSelectedSource(null);

    // Add user message to chat
    const userMessage: Message = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Call our API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          history: messages,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to get response');
      }

      // Add assistant message with sources
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Something went wrong'}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  // Sample questions
  const sampleQuestions = [
    'What are the ventilation requirements for a commercial kitchen?',
    'What are the requirements for a fire alarm system in a student dormitory?',
  ];

  // Get the last message's sources for the source list
  const lastAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-green-700 text-white p-4 shadow-md">
        <h1 className="text-xl font-bold">NYC Building Code Assistant</h1>
        <p className="text-sm text-green-100">Click on citation numbers to view source quotes</p>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat Area */}
        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Welcome message when no messages */}
          {messages.length === 0 && (
            <div className="text-center py-12">
              <h2 className="text-2xl font-semibold text-gray-700 mb-4">
                Welcome! Ask me about NYC Building Codes
              </h2>
              <p className="text-gray-500 mb-8">
                I can help you find specific code sections, requirements, and regulations.
                <br />
                <span className="text-sm text-gray-400">Click citation numbers to see the source quote.</span>
              </p>
              <div className="space-y-2">
                <p className="text-sm text-gray-400">Try a sample question:</p>
                {sampleQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(q)}
                    className="block mx-auto px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 text-sm"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message bubbles */}
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-green-700 text-white'
                    : 'bg-white border border-gray-200 text-gray-800'
                }`}
              >
                {/* Message content with interactive citations */}
                {message.role === 'assistant' ? (
                  <>
                    <MessageContent
                      content={message.content}
                      sources={message.sources}
                      selectedSource={selectedSource}
                      onSelectSource={handleSelectSource}
                    />

                    {/* Show selected source quote */}
                    {selectedSource && message.sources?.some(s => s.id === selectedSource.id) && (
                      <SourceQuotePanel
                        source={selectedSource}
                        onClose={() => setSelectedSource(null)}
                      />
                    )}
                  </>
                ) : (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg p-4 text-gray-500">
                <div className="flex items-center space-x-2">
                  <div className="animate-bounce">●</div>
                  <div className="animate-bounce" style={{ animationDelay: '0.1s' }}>●</div>
                  <div className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</div>
                  <span className="ml-2">Searching codes and generating response...</span>
                </div>
              </div>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </main>

        {/* Source List Sidebar */}
        {lastAssistantMessage?.sources && lastAssistantMessage.sources.length > 0 && (
          <aside className="w-80 bg-white border-l border-gray-200 overflow-y-auto hidden lg:block">
            <div className="p-4">
              <h3 className="font-semibold text-gray-700 mb-3">Codes</h3>
              <div className="space-y-2">
                {lastAssistantMessage.sources.slice(0, 5).map((source, i) => {
                  const shortName = formatCodeName(source.code_name);
                  const isSelected = selectedSource?.id === source.id;
                  return (
                    <button
                      key={i}
                      onClick={() => handleSelectSource(isSelected ? null : source)}
                      className={`w-full text-left p-2 rounded text-sm transition-colors ${
                        isSelected
                          ? 'bg-green-100 border border-green-300'
                          : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                      }`}
                    >
                      <span className="text-green-700 font-medium mr-2">{i + 1}</span>
                      <span className={isSelected ? 'text-green-800' : 'text-gray-700'}>
                        {shortName} {source.section}
                        {source.section_title && ` ${source.section_title}`}
                      </span>
                    </button>
                  );
                })}
                {lastAssistantMessage.sources.length > 5 && (
                  <details className="text-sm">
                    <summary className="text-green-700 cursor-pointer hover:underline">
                      +{lastAssistantMessage.sources.length - 5} more
                    </summary>
                    <div className="mt-2 space-y-2">
                      {lastAssistantMessage.sources.slice(5).map((source, i) => {
                        const shortName = formatCodeName(source.code_name);
                        const actualIndex = i + 5;
                        const isSelected = selectedSource?.id === source.id;
                        return (
                          <button
                            key={actualIndex}
                            onClick={() => handleSelectSource(isSelected ? null : source)}
                            className={`w-full text-left p-2 rounded text-sm transition-colors ${
                              isSelected
                                ? 'bg-green-100 border border-green-300'
                                : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                            }`}
                          >
                            <span className="text-green-700 font-medium mr-2">{actualIndex + 1}</span>
                            <span className={isSelected ? 'text-green-800' : 'text-gray-700'}>
                              {shortName} {source.section}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </details>
                )}
              </div>

              {/* Selected source quote display */}
              {selectedSource && (
                <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                  <h4 className="font-semibold text-green-800 text-sm mb-2">
                    {formatCodeName(selectedSource.code_name)} {selectedSource.section}
                    {selectedSource.section_title && ` ${selectedSource.section_title}`}
                  </h4>
                  <p className="text-xs text-gray-600 mb-2">{selectedSource.code_name}</p>
                  <div className="text-sm text-gray-700 max-h-64 overflow-y-auto bg-white p-2 rounded border">
                    {selectedSource.content}
                  </div>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* Input Area */}
      <footer className="bg-white border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about NYC building codes..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent text-black"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-green-700 text-white rounded-lg hover:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
