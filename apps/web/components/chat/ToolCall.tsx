'use client';

import { useMemo, useState } from 'react';
import { Tool, type ToolPart } from '@/components/ui/tool';

interface ToolCallProps {
  command: string;
  args?: string;
  status?: 'running' | 'complete' | 'error';
  output?: string;
  errorText?: string;
}

/**
 * ToolCall component - Wrapper around prompt-kit Tool component
 * Converts our legacy API to the prompt-kit ToolPart structure
 * 
 * Migration from custom component to prompt-kit Tool (2025-10-30)
 * - Uses AI SDK v5 compatible structure
 * - Better state management
 * - Improved accessibility
 * - Structured input/output display
 */
export function ToolCall({ command, args, status = 'running', output, errorText }: ToolCallProps) {
  // Clean up MCP tool names (remove mcp__firecrawl-tools__ prefix)
  const cleanName = command.replace(/^mcp__.*?__/, '');

  // Parse args string to object if it exists
  const parseArgs = (argsString?: string): Record<string, unknown> | undefined => {
    if (!argsString) return undefined;
    
    try {
      // Try to parse as JSON first
      return JSON.parse(argsString);
    } catch {
      // If not JSON, try to parse as key=value pairs
      const pairs = argsString.split(/[,\s]+/);
      const obj: Record<string, unknown> = {};
      
      for (const pair of pairs) {
        const [key, ...valueParts] = pair.split('=');
        if (key && valueParts.length > 0) {
          obj[key.trim()] = valueParts.join('=').trim();
        }
      }
      
      // If we got something, return it; otherwise return the raw string
      return Object.keys(obj).length > 0 ? obj : { args: argsString };
    }
  };

  // Generate stable tool ID using useState with lazy initializer (only called once)
  const [toolId] = useState(() => `tool-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  // Create ToolPart structure for prompt-kit Tool component
  const toolPart: ToolPart = useMemo(() => {
    // Convert legacy status to AI SDK v5 state (inlined to avoid stale closure)
    const getToolPartState = (): ToolPart['state'] => {
      switch (status) {
        case 'running':
          return 'input-streaming';
        case 'complete':
          return 'output-available';
        case 'error':
          return 'output-error';
        default:
          return 'input-available';
      }
    };

    // Parse output if it exists
    const parseOutput = (outputString?: string): Record<string, unknown> | undefined => {
      if (!outputString) return undefined;

      try {
        return JSON.parse(outputString);
      } catch {
        return { result: outputString };
      }
    };

    return {
      type: cleanName,
      state: getToolPartState(),
      input: parseArgs(args),
      output: parseOutput(output),
      toolCallId: toolId,
      errorText,
    };
  }, [cleanName, status, args, output, errorText, toolId]);

  return (
    <Tool 
      toolPart={toolPart} 
      defaultOpen={status === 'error'} // Auto-open on error
      className="my-2"
    />
  );
}
