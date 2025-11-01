/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/basic-features/typescript for more information.

declare namespace NodeJS {
  interface ProcessEnv {
    // Backend API
    NEXT_PUBLIC_API_URL: string;
    NEXT_PUBLIC_APP_URL: string;
    
    // Crawl Configuration
    NEXT_PUBLIC_CRAWL_MAX_DEPTH: string;
    NEXT_PUBLIC_CRAWL_MAX_PAGES: string;
    NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT: string;
    NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT: string;
    
    // Anthropic
    ANTHROPIC_API_KEY?: string;
    
    // Optional
    NEXT_PUBLIC_DEBUG?: string;
    NEXT_PUBLIC_GA_ID?: string;
    BACKEND_URL?: string;
  }
}
