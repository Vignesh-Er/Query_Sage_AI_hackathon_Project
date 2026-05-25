export interface ApiError {
  error: string;
  detail?: string;
}

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request<T>(
  path: string, 
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    }
  });

  if (!response.ok) {
    let errBody: ApiError;
    try {
      errBody = await response.json();
    } catch {
      errBody = { error: `HTTP ${response.status}: ${response.statusText}` };
    }
    throw errBody;
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  return response.json();
}

export const apiClient = {
  // Generic HTTP helpers
  get: <T = any>(path: string, options?: RequestInit) => request<T>(path, { ...options, method: "GET" }),
  post: <T = any>(path: string, data?: any, options?: RequestInit) => request<T>(path, { 
    ...options, 
    method: "POST", 
    body: data ? JSON.stringify(data) : undefined 
  }),
  patch: <T = any>(path: string, data?: any, options?: RequestInit) => request<T>(path, { 
    ...options, 
    method: "PATCH", 
    body: data ? JSON.stringify(data) : undefined 
  }),
  delete: <T = any>(path: string, options?: RequestInit) => request<T>(path, { ...options, method: "DELETE" }),

  // Connections CRUD
  getConnections: () => request<any[]>("/api/connections"),
  createConnection: (data: any) => request<any>("/api/connections", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  deleteConnection: (id: number) => request<void>(`/api/connections/${id}`, {
    method: "DELETE"
  }),
  testConnection: (id: number) => request<any>(`/api/connections/${id}/test`, {
    method: "POST"
  }),
  testConnectionUnsaved: (data: any) => request<any>("/api/connections/test", {
    method: "POST",
    body: JSON.stringify(data)
  }),

  // Schema Catalog
  getSchema: (id: number) => request<any>(`/api/schema/${id}`),
  checkSchemaImpact: (data: any) => request<any>("/api/schema/impact", {
    method: "POST",
    body: JSON.stringify(data)
  }),

  // Query History logs
  getHistory: (params: Record<string, any>) => {
    const q = new URLSearchParams(params).toString();
    return request<any[]>(`/api/history?${q}`);
  },
  getHistoryDetail: (id: number) => request<any>(`/api/history/${id}`),
  updateHistoryTags: (id: number, tags: string[]) => request<any>(`/api/history/${id}/tags`, {
    method: "POST",
    body: JSON.stringify(tags)
  }),

  // Scorecards
  getScorecard: () => request<any>("/api/score"),

  // Bulk uploads
  bulkAnalyze: (formData: FormData) => {
    return fetch(`${API_BASE}/api/bulk/analyze`, {
      method: "POST",
      body: formData
    }).then(res => {
      if (!res.ok) throw new Error("Bulk upload failed");
      return res.json();
    });
  },

  // Natural Language SQL
  generateSql: (data: any) => request<any>("/api/natural-language/generate", {
    method: "POST",
    body: JSON.stringify(data)
  }),

  // Settings Key-Value
  getSettings: () => request<any[]>("/api/settings"),
  patchSetting: (key: string, value: string) => request<any>(`/api/settings/${key}`, {
    method: "PATCH",
    body: JSON.stringify({ value })
  })
};
export const client = apiClient;
export default apiClient;
