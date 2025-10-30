"use client";

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { CommandsDropdown } from './CommandsDropdown';
import { MentionDropdown } from './MentionDropdown';
import { InputFooter } from './InputFooter';

interface ChatInputProps {
  onSend: (message: string) => void;
}

export function ChatInput({ onSend }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showCommands, setShowCommands] = useState(false);
  const [showMentions, setShowMentions] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = '36px';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [value]);

  // Handle input changes
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setValue(newValue);

    const cursorPosition = e.target.selectionStart;
    const textBeforeCursor = newValue.substring(0, cursorPosition);
    
    // Check for / command
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');
    const lastSpaceIndex = textBeforeCursor.lastIndexOf(' ');
    
    if (lastSlashIndex !== -1 && lastSlashIndex > lastSpaceIndex) {
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

  // Handle keyboard shortcuts
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Command dropdown navigation
    if (showCommands) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => Math.min(prev + 1, 6));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCommandIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Escape') {
        setShowCommands(false);
      }
      return;
    }

    // Enter to send (Shift+Enter for new line)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Global ⌘+K shortcut
  useEffect(() => {
    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handleSend = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue('');
    setShowCommands(false);
    setShowMentions(false);
  };

  const handleCommandSelect = (command: string) => {
    const cursorPosition = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');
    
    const newValue = value.substring(0, lastSlashIndex) + command + ' ' + value.substring(cursorPosition);
    setValue(newValue);
    setShowCommands(false);
    textareaRef.current?.focus();
  };

  const handleMentionSelect = (source: string) => {
    const cursorPosition = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    const newValue = value.substring(0, lastAtIndex) + `@${source} ` + value.substring(cursorPosition);
    setValue(newValue);
    setShowMentions(false);
    textareaRef.current?.focus();
  };

  return (
    <div className="relative pointer-events-none">
      <div className="absolute bottom-0 left-0 right-0 pb-6 pointer-events-auto">
        <div className="max-w-3xl mx-auto px-6">
          <div className="relative">
            {/* Dropdowns */}
            {showMentions && <MentionDropdown onSelect={handleMentionSelect} />}
            {showCommands && (
              <CommandsDropdown
                selectedIndex={selectedCommandIndex}
                onSelect={handleCommandSelect}
                onHover={setSelectedCommandIndex}
              />
            )}
            
            {/* Input Field */}
            <div className="relative flex items-end gap-2 p-2.5 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 focus-within:border-blue-500 dark:focus-within:border-blue-500 focus-within:shadow-lg focus-within:shadow-blue-500/10 dark:focus-within:shadow-blue-500/20 rounded-xl transition-all shadow-md dark:shadow-lg">
              <div className="flex items-center pb-0.5">
                <button
                  className="p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-all hover:scale-105"
                  title="Attach file"
                >
                  <svg className="w-4 h-4 text-zinc-500 dark:text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
                  </svg>
                </button>
              </div>
              
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder="Ask me anything... (Enter to send, Shift+Enter for new line)"
                value={value}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => setIsFocused(false), 150)}
                className="flex-1 bg-transparent px-2 py-1.5 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none resize-none max-h-[200px]"
                style={{ minHeight: '36px' }}
              />
              
              <div className="flex items-center gap-1 pb-0.5">
                <button
                  className="p-1.5 hover:bg-purple-50 dark:hover:bg-purple-500/10 rounded-lg transition-all hover:scale-105 group"
                  title="Enhance prompt with AI"
                >
                  <svg className="w-4 h-4 text-purple-500 dark:text-purple-400 group-hover:text-purple-600 dark:group-hover:text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                  </svg>
                </button>
                
                <button
                  onClick={handleSend}
                  disabled={!value.trim()}
                  className="p-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 disabled:from-zinc-300 disabled:to-zinc-300 dark:disabled:from-zinc-800 dark:disabled:to-zinc-800 disabled:cursor-not-allowed rounded-lg transition-all shadow-md shadow-blue-500/30 hover:shadow-lg hover:shadow-blue-500/50 hover:scale-105 disabled:shadow-none disabled:scale-100"
                >
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Input Footer */}
            <div className="flex items-center justify-between mt-2 px-1">
              <InputFooter isFocused={isFocused} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
