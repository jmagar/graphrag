/**
 * Utility functions for exporting chat messages to Markdown format
 */

interface ExportableMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string | string[];
  timestamp?: string;
  citations?: Array<{ number: number; title: string; url?: string }>;
}

/**
 * Converts a single message to Markdown format
 */
export function messageToMarkdown(message: ExportableMessage): string {
  const { role, content, timestamp, citations } = message;

  // Build header
  const header = role === 'user' ? '## User' : '## Assistant';
  const time = timestamp ? ` (${timestamp})` : '';

  // Build content
  const contentText = Array.isArray(content)
    ? content.join('\n\n')
    : content;

  // Build citations
  let citationsText = '';
  if (citations && citations.length > 0) {
    citationsText = '\n\n### Citations\n\n' + citations.map(c => {
      const urlPart = c.url ? ` - [${c.url}](${c.url})` : '';
      return `${c.number}. ${c.title}${urlPart}`;
    }).join('\n');
  }

  return `${header}${time}\n\n${contentText}${citationsText}\n\n---\n`;
}

/**
 * Converts an array of messages to a complete Markdown document
 */
export function messagesToMarkdown(messages: ExportableMessage[]): string {
  const date = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  const header = `# Chat Export\n\n**Exported:** ${date}\n\n---\n\n`;

  const body = messages.map(m => messageToMarkdown(m)).join('\n');

  return header + body;
}

/**
 * Downloads a string as a Markdown file
 */
export function downloadMarkdown(content: string, filename: string = 'chat-export.md'): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Exports messages to Markdown and triggers download
 */
export function exportMessagesToMarkdown(messages: ExportableMessage[]): void {
  const markdown = messagesToMarkdown(messages);
  const timestamp = new Date().toISOString().split('T')[0];
  const filename = `chat-export-${timestamp}.md`;

  downloadMarkdown(markdown, filename);
}
