"use client";

import { useState, useEffect, KeyboardEvent } from 'react';
import { CommandsDropdown } from './CommandsDropdown';
import { MentionDropdown } from './MentionDropdown';
import { InputFooter } from './InputFooter';
import { 
  PromptInput, 
  PromptInputTextarea, 
  PromptInputActions, 
  PromptInputAction 
} from '@/components/ui/prompt-input';
import { Button } from '@/components/ui/button';
import { Paperclip, Sparkles, Send } from 'lucide-react';

/**
 * ChatInput - Migrated to prompt-kit PromptInput (2025-10-30)
 * 
 * Benefits:
 * - Auto-resize textarea built-in
 * - Better keyboard handling
 * - Loading states
 * - Tooltip support for actions
 * - Accessibility improvements
 * 
 * Preserved Features:
 * - Command dropdown (/)
 * - Mention dropdown (@)
 * - Cmd+K focus shortcut
 * - Enter to send, Shift+Enter for newline
 * - Custom attach and enhance buttons
 */

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
}

export function ChatInput({ onSend, isLoading = false }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showCommands, setShowCommands] = useState(false);
  const [showMentions, setShowMentions] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const [filteredCommands, setFilteredCommands] = useState<string[]>([]);

  // All available commands
  const allCommands = ['/scrape', '/crawl', '/map', '/search', '/extract'];

  // Handle input changes for command/mention detection
  const handleValueChange = (newValue: string) => {
    setValue(newValue);

    // Get cursor position (we'll use end of string as approximation)
    const cursorPosition = newValue.length;
    const textBeforeCursor = newValue.substring(0, cursorPosition);
    
    // Check for / command
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');
    const lastSpaceIndex = textBeforeCursor.lastIndexOf(' ');
    
    if (lastSlashIndex !== -1 && lastSlashIndex > lastSpaceIndex) {
      // Extract the text after the slash
      const commandText = textBeforeCursor.substring(lastSlashIndex + 1).toLowerCase();
      
      // Filter commands based on what user typed
      const filtered = allCommands.filter(cmd => 
        cmd.toLowerCase().substring(1).startsWith(commandText) || 
        cmd.toLowerCase().includes(commandText)
      );
      
      setFilteredCommands(filtered.length > 0 ? filtered : allCommands);
      setShowCommands(true);
      setShowMentions(false);
      setSelectedCommandIndex(0);
      return;
    }
    
    // Check for @ mention
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    if (lastAtIndex !== -1 && lastAtIndex > lastSpaceIndex) {
      setShowMentions(true);
      setShowCommands(false);
    } else {
      setShowMentions(false);
      setShowCommands(false);
    }
  };

  // Handle keyboard shortcuts in textarea
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Escape key closes dropdowns
    if (e.key === 'Escape') {
      e.preventDefault();
      setShowCommands(false);
      setShowMentions(false);
      return;
    }

    // Command dropdown navigation
    if (showCommands) {
      const commandsToUse = filteredCommands.length > 0 ? filteredCommands : allCommands;
      const maxIndex = commandsToUse.length - 1;
      
      if (e.key === 'Tab') {
        // Tab cycles through commands
        e.preventDefault();
        setSelectedCommandIndex((prev) => (prev + 1) % commandsToUse.length);
        return;
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => Math.min(prev + 1, maxIndex));
        return;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => Math.max(prev - 1, 0));
        return;
      } else if (e.key === 'Enter' && !e.shiftKey) {
        // Enter selects command if dropdown is open
        e.preventDefault();
        if (commandsToUse[selectedCommandIndex]) {
          handleCommandSelect(commandsToUse[selectedCommandIndex]);
        }
        return;
      } else if (e.key.length === 1 && e.key.match(/[a-z]/i)) {
        // Type a letter to jump to closest matching command
        e.preventDefault();
        const letter = e.key.toLowerCase();
        
        const commandNames = commandsToUse.map(cmd => cmd.substring(1));
        let foundIndex = commandNames.findIndex(cmd => cmd.startsWith(letter));
        
        if (foundIndex === -1) {
          foundIndex = commandNames.findIndex(cmd => cmd.includes(letter));
        }
        
        if (foundIndex !== -1) {
          setSelectedCommandIndex(foundIndex);
        }
        return;
      }
    }

    // Mention dropdown navigation
    if (showMentions && (e.key === 'ArrowDown' || e.key === 'ArrowUp' || (e.key === 'Enter' && !e.shiftKey))) {
      e.preventDefault();
      // TODO: Add mention navigation when needed
      return;
    }
  };

  // Global Cmd+K shortcut
  useEffect(() => {
    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        // Focus will be handled by PromptInput's textareaRef
        const textarea = document.querySelector('textarea[placeholder="Ask me anything..."]') as HTMLTextAreaElement;
        textarea?.focus();
      }
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handleSend = () => {
    if (!value.trim() || isLoading) return;
    onSend(value);
    setValue('');
    setShowCommands(false);
    setShowMentions(false);
  };

  const handleCommandSelect = (command: string) => {
    const lastSlashIndex = value.lastIndexOf('/');
    const newValue = value.substring(0, lastSlashIndex) + command + ' ';
    setValue(newValue);
    setShowCommands(false);
  };

  const handleMentionSelect = (source: string) => {
    const lastAtIndex = value.lastIndexOf('@');
    const newValue = value.substring(0, lastAtIndex) + `@${source} `;
    setValue(newValue);
    setShowMentions(false);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-10 pointer-events-none">
      <div className="pb-4 md:pb-6 pointer-events-auto bg-gradient-to-t from-zinc-50 via-zinc-50 to-transparent dark:from-zinc-900 dark:via-zinc-900 dark:to-transparent pt-8">
        <div className="max-w-3xl mx-auto px-3 md:px-6">
          <div className="relative">
            {/* Dropdowns */}
            {showMentions && <MentionDropdown onSelect={handleMentionSelect} />}
            {showCommands && (
              <CommandsDropdown
                selectedIndex={selectedCommandIndex}
                onSelect={handleCommandSelect}
                onHover={setSelectedCommandIndex}
                filteredCommands={filteredCommands.length > 0 ? filteredCommands : allCommands}
              />
            )}
            
            {/* Prompt Input with Actions */}
            <PromptInput
              value={value}
              onValueChange={handleValueChange}
              onSubmit={handleSend}
              isLoading={isLoading}
              className="shadow-lg border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 focus-within:border-blue-500 dark:focus-within:border-blue-500 focus-within:shadow-xl focus-within:shadow-blue-500/10 dark:focus-within:shadow-blue-500/20"
            >
              <div className="flex items-end gap-2 w-full">
                {/* Attach button - hidden on small mobile */}
                <div className="hidden sm:flex items-center pb-1">
                  <PromptInputAction tooltip="Attach file" side="top">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      className="h-8 w-8 p-0 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                      disabled={isLoading}
                    >
                      <Paperclip className="h-4 w-4 text-zinc-500 dark:text-zinc-400" />
                    </Button>
                  </PromptInputAction>
                </div>

                {/* Textarea */}
                <div className="flex-1">
                  <PromptInputTextarea
                    placeholder="Ask me anything..."
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setTimeout(() => setIsFocused(false), 150)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                    className="min-h-[44px] max-h-[200px] text-base md:text-sm"
                  />
                </div>

                {/* Actions */}
                <PromptInputActions className="pb-1">
                  {/* Enhance button - hidden on mobile */}
                  <div className="hidden md:block">
                    <PromptInputAction tooltip="Enhance prompt with AI" side="top">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        className="h-8 w-8 p-0 hover:bg-purple-50 dark:hover:bg-purple-500/10"
                        disabled={isLoading}
                      >
                        <Sparkles className="h-4 w-4 text-purple-500 dark:text-purple-400" />
                      </Button>
                    </PromptInputAction>
                  </div>

                  {/* Send button */}
                  <Button
                    onClick={handleSend}
                    disabled={!value.trim() || isLoading}
                    size="sm"
                    aria-label="Send message"
                    className="h-9 w-9 p-0 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 disabled:from-zinc-300 disabled:to-zinc-300 dark:disabled:from-zinc-800 dark:disabled:to-zinc-800 shadow-md shadow-blue-500/30 hover:shadow-lg hover:shadow-blue-500/50"
                  >
                    <Send className="h-4 w-4 text-white" aria-hidden="true" />
                  </Button>
                </PromptInputActions>
              </div>
            </PromptInput>
            
            {/* Input Footer - hidden on mobile */}
            <div className="hidden md:flex items-center justify-between mt-2 px-1">
              <InputFooter isFocused={isFocused} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
