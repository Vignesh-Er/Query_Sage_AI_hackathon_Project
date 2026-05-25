import { useState, useEffect, useCallback } from "react";
import apiClient from "../api/client";

export function useScore() {
  const [scorecard, setScorecard] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScorecard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getScorecard();
      setScorecard(data);
    } catch (err: any) {
      setError(err.error || "Failed to load score details.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScorecard();
  }, [fetchScorecard]);

  return {
    scorecard,
    loading,
    error,
    refetch: fetchScorecard
  };
}
export default useScore;
