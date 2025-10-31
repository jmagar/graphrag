"use client";

import { useEffect, useState } from "react";

interface CollectionInfo {
  name: string;
  vectors_count: number;
  points_count: number;
  segments_count: number;
  status: string;
}

// Format number to readable format (K, M) at module scope to prevent recreation on every render
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
};

export function StatisticsSection() {
  const [stats, setStats] = useState<CollectionInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true);
        const response = await fetch("/api/stats");
        
        if (!response.ok) {
          throw new Error("Failed to fetch statistics");
        }
        
        const data = await response.json();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        console.error("Failed to fetch stats:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4 border-b border-zinc-200 dark:border-zinc-800/80">
      <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
        Statistics
      </div>
      
      {isLoading && !stats && (
        <div className="text-xs text-zinc-500 dark:text-zinc-400 py-2">
          Loading...
        </div>
      )}
      
      {error && (
        <div className="text-xs text-red-500 dark:text-red-400 py-2">
          {error}
        </div>
      )}
      
      {stats && (
        <div className="space-y-1">
          <div className="flex items-center justify-between py-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-400">Documents</span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              {formatNumber(stats.points_count)}
            </span>
          </div>
          <div className="flex items-center justify-between py-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-400">Vectors</span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              {formatNumber(stats.vectors_count)}
            </span>
          </div>
          <div className="flex items-center justify-between py-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-400">Segments</span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              {formatNumber(stats.segments_count)}
            </span>
          </div>
          <div className="flex items-center justify-between py-1 text-xs">
            <span className="text-zinc-600 dark:text-zinc-400">Status</span>
            <span className={`font-semibold ${
              stats.status === "green" 
                ? "text-emerald-600 dark:text-emerald-400" 
                : stats.status === "yellow"
                ? "text-yellow-600 dark:text-yellow-400"
                : "text-red-600 dark:text-red-400"
            }`}>
              {stats.status}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
