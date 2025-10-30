import { query } from "@anthropic-ai/claude-agent-sdk";
import { NextRequest } from "next/server";
import { firecrawlServer } from "@/lib/firecrawl-tools";

interface ChatRequest {
  message: string;
  sessionId?: string; // Claude Agent SDK session ID for resuming
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { message, sessionId } = body;

    if (!message || typeof message !== "string") {
      return new Response(
        JSON.stringify({ error: "Message is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Create a ReadableStream for SSE (Server-Sent Events)
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Query Claude Agent SDK with MCP tools
          // SDK manages conversation state - just resume if sessionId provided
          const agentQuery = query({
            prompt: message, // Just the current message
            options: {
              ...(sessionId && { resume: sessionId }), // Resume existing session
              maxTurns: 10,
              includePartialMessages: true, // Enable streaming for live updates
              permissionMode: "bypassPermissions", // Auto-approve for chat
              systemPrompt: `You are a helpful AI assistant for GraphRAG, a system that combines graph databases with retrieval-augmented generation.

You help users understand and work with:
- Firecrawl for web crawling and scraping
- Qdrant vector database for semantic search
- TEI (Text Embeddings Inference) for embeddings
- The GraphRAG architecture and workflows

You have access to powerful tools:
- scrape_url: Get content from a single webpage
- map_website: List all URLs on a site (discover structure)
- search_web: Search the web and get full page content
- extract_structured_data: Extract specific data fields using natural language
- start_crawl: Index an entire website into Qdrant (async background job)
- check_crawl_status: Monitor crawl progress
- query_knowledge_base: Search previously crawled/indexed content in Qdrant

Use these tools proactively to help users. For example:
- If they ask about a website, use scrape_url or map_website
- If they want to index a site, use start_crawl
- If they ask about previously crawled content, use query_knowledge_base

Be concise, helpful, and technical when appropriate.`,
              
              // Enable Firecrawl MCP tools
              mcpServers: {
                "firecrawl-tools": firecrawlServer
              },
              
              // Allow all Firecrawl tools
              allowedTools: [
                "mcp__firecrawl-tools__scrape_url",
                "mcp__firecrawl-tools__map_website",
                "mcp__firecrawl-tools__search_web",
                "mcp__firecrawl-tools__extract_structured_data",
                "mcp__firecrawl-tools__start_crawl",
                "mcp__firecrawl-tools__check_crawl_status",
                "mcp__firecrawl-tools__query_knowledge_base"
              ]
            },
          });

          // Stream messages from Claude Agent SDK
          for await (const msg of agentQuery) {
            // Capture session ID from init message for client to resume later
            if (msg.type === 'system' && msg.subtype === 'init') {
              const sessionData = JSON.stringify({
                type: 'session_init',
                session_id: msg.session_id
              });
              controller.enqueue(encoder.encode(`data: ${sessionData}\n\n`));
            }
            
            // Send all message types to frontend
            const data = JSON.stringify(msg);
            controller.enqueue(encoder.encode(`data: ${data}\n\n`));

            // If this is a final result, close the stream
            if (msg.type === "result") {
              controller.enqueue(encoder.encode("data: [DONE]\n\n"));
              break;
            }
          }

          controller.close();
        } catch (error: any) {
          console.error("Chat error:", error);
          const errorData = JSON.stringify({
            type: "error",
            error: error.message || "An error occurred",
          });
          controller.enqueue(encoder.encode(`data: ${errorData}\n\n`));
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error: any) {
    console.error("Request error:", error);
    return new Response(
      JSON.stringify({ error: error.message || "Internal server error" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
