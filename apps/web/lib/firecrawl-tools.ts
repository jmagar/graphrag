import { createSdkMcpServer, tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import axios from "axios";

const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4400";

/**
 * Custom MCP server providing Firecrawl and GraphRAG tools to Claude.
 * 
 * These tools allow Claude to:
 * - Scrape web pages
 * - Map website structures  
 * - Search the web
 * - Extract structured data
 * - Start crawl jobs
 * - Check crawl status
 * - Query the knowledge base (Qdrant)
 */
export const firecrawlServer = createSdkMcpServer({
  name: "firecrawl-tools",
  version: "1.0.0",
  tools: [
    // Tool 1: Scrape URL
    tool(
      "scrape_url",
      "Scrape content from a single URL and return markdown. Use this when the user wants to extract content from a specific webpage.",
      {
        url: z.string().url().describe("The URL to scrape"),
        formats: z.array(z.enum(["markdown", "html"])).default(["markdown"]).describe("Content formats to retrieve")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/scrape/`, {
            url: args.url,
            formats: args.formats
          }, { timeout: 60000 });
          
          const markdown = response.data.data?.markdown || response.data.data?.html || "";
          
          // Truncate very long content to avoid context limits
          const truncated = markdown.length > 8000 
            ? markdown.substring(0, 8000) + "\n\n[Content truncated to fit context. Use extract_structured_data for specific fields.]"
            : markdown;
          
          return {
            content: [{
              type: "text",
              text: `Scraped content from ${args.url}:\n\n${truncated}`
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Failed to scrape ${args.url}: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 2: Map Website
    tool(
      "map_website",
      "Get a list of all URLs found on a website. Use this when the user wants to see the structure or sitemap of a website.",
      {
        url: z.string().url().describe("The website URL to map"),
        limit: z.number().default(100).describe("Maximum number of URLs to return")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/map/`, {
            url: args.url,
            limit: args.limit
          }, { timeout: 60000 });
          
          const urls = response.data.urls || [];
          const displayUrls = urls.slice(0, 50);
          
          return {
            content: [{
              type: "text",
              text: `Found ${urls.length} URLs on ${args.url}:\n\n${displayUrls.join('\n')}${urls.length > 50 ? `\n\n... and ${urls.length - 50} more URLs (total: ${urls.length})` : ""}`
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Failed to map ${args.url}: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 3: Search Web
    tool(
      "search_web",
      "Search the web and get full page content for results. Use this when the user needs to find information across multiple web pages.",
      {
        query: z.string().describe("The search query"),
        limit: z.number().default(5).describe("Number of results to return (1-10)")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/search/`, {
            query: args.query,
            limit: Math.min(args.limit, 10),
            formats: ["markdown"]
          }, { timeout: 60000 });
          
          const results = response.data.results || [];
          
          if (results.length === 0) {
            return {
              content: [{
                type: "text",
                text: `No results found for "${args.query}"`
              }]
            };
          }
          
          interface SearchResult {
            title: string;
            url: string;
            content: string;
          }
          const formatted = results.map((r: SearchResult, i: number) => {
            const preview = r.content.substring(0, 500);
            return `${i + 1}. **${r.title}**\n   URL: ${r.url}\n   ${preview}...`;
          }).join('\n\n');
          
          return {
            content: [{
              type: "text",
              text: `Search results for "${args.query}":\n\n${formatted}`
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Search failed: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 4: Extract Structured Data
    tool(
      "extract_structured_data",
      "Extract structured data from a webpage using natural language description. Use this when the user wants specific data fields from a page.",
      {
        url: z.string().url().describe("The URL to extract data from"),
        schema_description: z.string().describe("Natural language description of what to extract (e.g., 'article titles and publish dates', 'product names and prices')")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/extract/`, {
            url: args.url,
            schema: { extract: args.schema_description },
            formats: ["markdown"]
          }, { timeout: 90000 });
          
          const data = response.data.data || {};
          const jsonStr = JSON.stringify(data, null, 2);
          
          return {
            content: [{
              type: "text",
              text: `Extracted data from ${args.url}:\n\n\`\`\`json\n${jsonStr}\n\`\`\``
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Extraction failed: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 5: Start Crawl Job
    tool(
      "start_crawl",
      "Start an async crawl job to process an entire website. Pages are automatically embedded and stored in Qdrant for later querying. Use this when the user wants to index a whole site into the knowledge base.",
      {
        url: z.string().url().describe("The website URL to crawl"),
        max_depth: z.number().default(2).describe("Maximum crawl depth (1-5)"),
        max_pages: z.number().default(10).describe("Maximum number of pages to crawl (1-100)")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/crawl`, {
            url: args.url,
            maxDepth: Math.min(Math.max(args.max_depth, 1), 5),
            limit: Math.min(Math.max(args.max_pages, 1), 100)
          });
          
          const jobId = response.data.id || response.data.jobId;
          
          return {
            content: [{
              type: "text",
              text: `✅ Crawl job started for ${args.url}\n\n` +
                `Job ID: ${jobId}\n` +
                `Max depth: ${args.max_depth}\n` +
                `Max pages: ${args.max_pages}\n\n` +
                `Pages will be automatically:\n` +
                `1. Crawled by Firecrawl\n` +
                `2. Embedded using TEI\n` +
                `3. Stored in Qdrant vector database\n\n` +
                `Use check_crawl_status to monitor progress, or query_knowledge_base to search the indexed content once complete.`
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Failed to start crawl: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 6: Check Crawl Status
    tool(
      "check_crawl_status",
      "Check the status of a crawl job. Use this to monitor progress of a running crawl.",
      {
        job_id: z.string().describe("The crawl job ID")
      },
      async (args) => {
        try {
          const response = await axios.get(`${backendUrl}/api/v1/crawl/${args.job_id}`);
          
          const status = response.data;
          const progress = status.total > 0 
            ? Math.round((status.completed / status.total) * 100)
            : 0;
          
          return {
            content: [{
              type: "text",
              text: `📊 Crawl Job Status (${args.job_id}):\n\n` +
                `Status: ${status.status}\n` +
                `Progress: ${progress}% (${status.completed} / ${status.total} pages)\n` +
                `Credits Used: ${status.creditsUsed || 0}\n` +
                `Expires: ${status.expiresAt ? new Date(status.expiresAt).toLocaleString() : 'N/A'}\n\n` +
                (status.status === 'completed' 
                  ? `✅ Crawl complete! All pages have been embedded and stored in Qdrant. Use query_knowledge_base to search the content.`
                  : status.status === 'failed'
                  ? `❌ Crawl failed.`
                  : `⏳ Crawl in progress... Pages are being processed in the background.`)
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Failed to get crawl status: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    ),

    // Tool 7: Query Knowledge Base
    tool(
      "query_knowledge_base",
      "Search the Qdrant knowledge base for relevant content from previously crawled websites. This performs semantic search using embeddings. Use this to find information from crawled/indexed sites.",
      {
        query: z.string().describe("The search query"),
        limit: z.number().default(5).describe("Number of results to return (1-10)"),
        score_threshold: z.number().default(0.5).describe("Minimum similarity score (0-1). Higher = more relevant")
      },
      async (args) => {
        try {
          const response = await axios.post(`${backendUrl}/api/v1/query/`, {
            query: args.query,
            limit: Math.min(args.limit, 10),
            score_threshold: args.score_threshold,
            use_llm: false // Just return raw results, Claude will interpret
          });
          
          const results = response.data.results || [];
          
          if (results.length === 0) {
            return {
              content: [{
                type: "text",
                text: `No relevant content found in the knowledge base for "${args.query}". The knowledge base may be empty or the query may not match indexed content.`
              }]
            };
          }
          
          interface QueryResult {
            score: number;
            content: string;
            metadata?: { sourceURL?: string };
          }
          const formatted = results.map((r: QueryResult, i: number) => {
            return `${i + 1}. [Score: ${(r.score * 100).toFixed(0)}%] ${r.metadata?.sourceURL || 'Unknown source'}\n${r.content.substring(0, 500)}...`;
          }).join('\n\n---\n\n');
          
          return {
            content: [{
              type: "text",
              text: `Found ${results.length} relevant results in the knowledge base for "${args.query}":\n\n${formatted}`
            }]
          };
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const axiosError = error as { response?: { data?: { detail?: string } } };
          return {
            content: [{
              type: "text",
              text: `Knowledge base query failed: ${axiosError.response?.data?.detail || errorMessage}`
            }]
          };
        }
      }
    )
  ]
});
