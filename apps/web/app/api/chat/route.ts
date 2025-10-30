import { query } from "@anthropic-ai/claude-agent-sdk";
import { NextRequest } from "next/server";

interface ChatRequest {
  message: string;
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { message } = body;

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
          // Query Claude Agent SDK with simple string prompt
          // This spawns the local Claude Code CLI process
          const agentQuery = query({
            prompt: message, // Simple string prompt works!
            options: {
              maxTurns: 10,
              includePartialMessages: true, // Enable streaming for live updates
              permissionMode: "bypassPermissions", // Auto-approve for chat
              systemPrompt: `You are a helpful AI assistant for GraphRAG, a system that combines graph databases with retrieval-augmented generation.

You help users understand and work with:
- Firecrawl for web crawling and scraping
- Qdrant vector database for semantic search
- TEI (Text Embeddings Inference) for embeddings
- The GraphRAG architecture and workflows

Be concise, helpful, and technical when appropriate.`,
            },
          });

          // Stream messages from Claude Code CLI
          for await (const msg of agentQuery) {
            // Send different message types to frontend
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
