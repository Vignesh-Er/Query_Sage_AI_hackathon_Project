import { useState, useEffect } from "react";
import apiClient from "../api/client";

export function useSchemaFetch(connectionId: number | null) {
  const [schema, setSchema] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSchema = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getSchema(id);
      setSchema(data);
    } catch (err: any) {
      setError(err.error || "Failed to load database schema.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (connectionId) {
      fetchSchema(connectionId);
    } else {
      setSchema(null);
    }
  }, [connectionId]);

  return { schema, loading, error, refetch: () => connectionId && fetchSchema(connectionId) };
}
export default useSchemaFetch;
