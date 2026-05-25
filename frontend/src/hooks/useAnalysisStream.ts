import { useState } from "react";

export interface StreamStatus {
  stage: string;
  message: string;
}

export function useAnalysisStream() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<StreamStatus>({ stage: "", message: "" });
  const [findings, setFindings] = useState<any[]>([]);
  const [plan, setPlan] = useState<any>(null);
  const [regression, setRegression] = useState<any>(null);
  const [workload, setWorkload] = useState<any>(null);
  const [rewrite, setRewrite] = useState<any>(null);
  const [equivalence, setEquivalence] = useState<any>(null);
  const [complete, setComplete] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const startAnalysis = async (payload: {
    query: string;
    connectionId?: number | null;
    connection_id?: number | null;
    includePlan?: boolean;
    include_execution_plan?: boolean;
    verifyEquivalence?: boolean;
    verify_equivalence?: boolean;
    orm_framework?: string | null;
  }) => {
    setLoading(true);
    setError(null);
    setStatus({ stage: "parsing", message: "Starting analysis..." });
    setFindings([]);
    setPlan(null);
    setRegression(null);
    setWorkload(null);
    setRewrite(null);
    setEquivalence(null);
    setComplete(null);

    const API_BASE = import.meta.env.VITE_API_BASE || "";

    const requestPayload = {
      query: payload.query,
      connection_id: payload.connection_id !== undefined ? payload.connection_id : payload.connectionId,
      include_execution_plan: payload.include_execution_plan !== undefined ? payload.include_execution_plan : (payload.includePlan ?? true),
      verify_equivalence: payload.verify_equivalence !== undefined ? payload.verify_equivalence : (payload.verifyEquivalence ?? false),
      orm_framework: payload.orm_framework
    };

    try {
      const response = await fetch(`${API_BASE}/api/analyze/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestPayload)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable.");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.trim()) continue;

          const lines = part.split("\n");
          let eventType = "";
          let eventData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.replace("event: ", "").trim();
            } else if (line.startsWith("data: ")) {
              eventData = line.replace("data: ", "").trim();
            }
          }

          if (eventType && eventData) {
            try {
              const data = JSON.parse(eventData);
              switch (eventType) {
                case "status":
                  setStatus(data);
                  break;
                case "finding":
                  setFindings(prev => [...prev, data]);
                  break;
                case "plan":
                  setPlan(data);
                  break;
                case "regression":
                  setRegression(data);
                  break;
                case "workload":
                  setWorkload(data);
                  break;
                case "rewrite":
                  setRewrite(data);
                  break;
                case "equivalence":
                  setEquivalence(data);
                  break;
                case "complete":
                  setComplete(data);
                  setLoading(false);
                  break;
              }
            } catch (err) {
              console.error("Failed to parse event JSON:", err);
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || "Analysis stream disconnected unexpectedly.");
      setLoading(false);
    }
  };

  const clearAnalysis = () => {
    setLoading(false);
    setError(null);
    setStatus({ stage: "", message: "" });
    setFindings([]);
    setPlan(null);
    setRegression(null);
    setWorkload(null);
    setRewrite(null);
    setEquivalence(null);
    setComplete(null);
  };

  const streamState = {
    status,
    findings,
    plan,
    regression,
    workload,
    rewrite,
    equivalence,
    complete,
    error
  };

  return {
    streamState,
    isAnalyzing: loading,
    startAnalysis,
    clearAnalysis
  };
}
export default useAnalysisStream;
