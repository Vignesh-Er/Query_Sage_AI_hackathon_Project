import { useState, useEffect, useCallback } from "react";
import apiClient from "../api/client";

export function useHistory() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, any>>({
    page: 1,
    page_size: 15
  });

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getHistory(filters);
      setHistory(data);
    } catch (err: any) {
      setError(err.error || "Failed to load queries history.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const updateFilters = (newFilters: Record<string, any>) => {
    setFilters(prev => ({ ...prev, ...newFilters, page: 1 }));
  };

  const nextPage = () => {
    setFilters(prev => ({ ...prev, page: prev.page + 1 }));
  };

  const prevPage = () => {
    setFilters(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }));
  };

  return {
    history,
    loading,
    error,
    filters,
    updateFilters,
    nextPage,
    prevPage,
    refetch: fetchHistory
  };
}
export default useHistory;
