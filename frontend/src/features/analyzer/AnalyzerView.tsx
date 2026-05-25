import React, { useState, useEffect } from "react";
import { TOKENS } from "../../design-system/tokens";
import { ToolbarStrip } from "./ToolbarStrip";
import { FindingCard } from "./FindingCard";
import { RegressionBanner } from "./RegressionBanner";
import { DiffView } from "./DiffView";
import { IndexRecommendations } from "./IndexRecommendations";
import { EquivalenceResult } from "./EquivalenceResult";
import { Card } from "../../design-system/components/Card";
import { useAnalysisStream } from "../../hooks/useAnalysisStream";
import { Suspense, lazy } from "react";
import { SkeletonCard } from "../../design-system/components/SkeletonCard";
import { Activity, AlertOctagon, Cpu, Code2, Play, X } from "lucide-react";

const MonacoEditorComponent = lazy(() => import("./MonacoEditorComponent"));
const PlanTreeVisualizer = lazy(() => import("./PlanTreeVisualizer"));

interface AnalyzerViewProps {
  initialQuery?: string;
  connections: Array<{ id: number; name: string; engine: string }>;
  selectedConnectionId: number | null;
  onSelectConnection: (id: number | null) => void;
}

export const AnalyzerView: React.FC<AnalyzerViewProps> = ({
  initialQuery = "SELECT * FROM rental WHERE YEAR(rental_date) = 2005;",
  connections,
  selectedConnectionId,
  onSelectConnection
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [includePlan, setIncludePlan] = useState(true);
  const [verifyEquivalence, setVerifyEquivalence] = useState(false);

  // Monaco references
  const [editorRef, setEditorRef] = useState<any>(null);
  const [monacoRef, setMonacoRef] = useState<any>(null);
  const [lintFindings, setLintFindings] = useState<any[]>([]);

  // LSP State
  const [lspAvailable, setLspAvailable] = useState(true);
  const [showLspBanner, setShowLspBanner] = useState(false);

  // What-If Simulation State
  const [indexStmt, setIndexStmt] = useState("");
  const [whatIfResult, setWhatIfResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Load stream state hooks
  const {
    streamState,
    isAnalyzing,
    startAnalysis,
    clearAnalysis
  } = useAnalysisStream();

  useEffect(() => {
    if (!editorRef) return;
    
    // Attempt WebSocket connection to /api/lsp
    const rawBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8421";
    const wsUrl = rawBase
      .replace("http://", "ws://")
      .replace("https://", "wss://");
      
    const socket = new WebSocket(`${wsUrl}/api/lsp`);
    
    socket.onopen = () => {
      console.log("LSP proxy connection established.");
    };
    
    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.status === "error" && msg.code === "LSP_BINARY_MISSING") {
          setLspAvailable(false);
          setShowLspBanner(true);
        }
      } catch (err) {
        // Raw text stream from sqls stdout (JSON-RPC data)
      }
    };
    
    socket.onerror = () => {
      setLspAvailable(false);
      setShowLspBanner(true);
    };
    
    return () => {
      socket.close();
    };
  }, [editorRef]);

  // Debounced static linter call
  useEffect(() => {
    if (!query.trim()) {
      setLintFindings([]);
      return;
    }
    const delayDebounceFn = setTimeout(async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE || ""}/api/analyze/lint`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            query: query,
            connection_id: selectedConnectionId
          })
        });
        if (response.ok) {
          const findings = await response.json();
          setLintFindings(findings);
        }
      } catch (err) {
        console.error("Lint error:", err);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [query, selectedConnectionId]);

  // Model markers hook
  useEffect(() => {
    if (editorRef && monacoRef) {
      const model = editorRef.getModel();
      if (model) {
        const markers = lintFindings.map((f: any) => {
          const startPos = f.location_start ? model.getPositionAt(f.location_start) : { lineNumber: 1, column: 1 };
          const endPos = f.location_end ? model.getPositionAt(f.location_end) : { lineNumber: 1, column: 100 };
          return {
            severity: f.severity >= 8 ? monacoRef.MarkerSeverity.Error : monacoRef.MarkerSeverity.Warning,
            message: `${f.rule_id}: ${f.title} - ${f.description}`,
            startLineNumber: startPos.lineNumber,
            startColumn: startPos.column,
            endLineNumber: endPos.lineNumber,
            endColumn: endPos.column
          };
        });
        monacoRef.editor.setModelMarkers(model, "owner", markers);
      }
    }
  }, [lintFindings, editorRef, monacoRef]);

  const handleFormat = () => {
    // Basic sql formatting simulation
    const formatted = query
      .replace(/\bselect\b/gi, "SELECT")
      .replace(/\bfrom\b/gi, "\nFROM")
      .replace(/\bwhere\b/gi, "\nWHERE")
      .replace(/\bjoin\b/gi, "\nJOIN")
      .replace(/\band\b/gi, "\n  AND")
      .replace(/\bor\b/gi, "\n  OR");
    setQuery(formatted);
  };

  const handleClear = () => {
    setQuery("");
    clearAnalysis();
  };

  const handleAnalyze = () => {
    startAnalysis({
      query,
      connectionId: selectedConnectionId,
      includePlan,
      verifyEquivalence
    });
  };

  const handleSimulateWhatIf = async () => {
    if (!indexStmt.trim() || !selectedConnectionId) return;
    setIsSimulating(true);
    setWhatIfResult(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE || ""}/api/analyze/what-if`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: query,
          index_statement: indexStmt,
          connection_id: selectedConnectionId
        })
      });
      const data = await response.json();
      setWhatIfResult(data);
    } catch (err) {
      console.error("Simulation failed:", err);
      setWhatIfResult({
        success: false,
        error: "Failed to connect to the backend server."
      });
    } finally {
      setIsSimulating(false);
    }
  };

  // Determine stage progress percentage
  const getProgressPercentage = () => {
    const stage = streamState.status?.stage;
    if (!stage) return 0;
    switch (stage) {
      case "parsing": return 20;
      case "executing": return 40;
      case "workload": return 60;
      case "ai": return 80;
      case "equivalence": return 95;
      case "complete": return 100;
      default: return 0;
    }
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-abyss" style={{ fontFamily: TOKENS.fonts.ui }}>
      {/* Editor control toolbar */}
      <ToolbarStrip
        connections={connections}
        selectedConnectionId={selectedConnectionId}
        onSelectConnection={onSelectConnection}
        includePlan={includePlan}
        onToggleIncludePlan={setIncludePlan}
        verifyEquivalence={verifyEquivalence}
        onToggleVerifyEquivalence={setVerifyEquivalence}
        onFormat={handleFormat}
        onClear={handleClear}
        onAnalyze={handleAnalyze}
        isAnalyzing={isAnalyzing}
      />

      {/* Progress status loader bar */}
      {isAnalyzing && (
        <div className="w-full bg-trench h-1.5 relative overflow-hidden">
          <div 
            className="h-full bg-ember transition-all duration-300 shadow-[0_0_8px_#E8860A]"
            style={{ width: `${getProgressPercentage()}%` }}
          />
        </div>
      )}

      {/* Monaco LSP Graceful Degradation Dismissible Banner */}
      {showLspBanner && !lspAvailable && (
        <div 
          className="p-3 border-b flex items-center justify-between text-xs font-ui transition-all"
          style={{
            backgroundColor: `${TOKENS.colors.sulfur}0D`,
            borderColor: TOKENS.colors.border,
            color: TOKENS.colors.text.primary
          }}
        >
          <div className="flex items-center gap-2">
            <AlertOctagon size={16} className="text-sulfur shrink-0" />
            <span>
              LSP features unavailable. Install{" "}
              <a 
                href="https://github.com/lighttiger2505/sqls" 
                target="_blank" 
                rel="noopener noreferrer"
                className="underline hover:text-ember transition-colors font-semibold"
              >
                sqls
              </a>{" "}
              for column autocomplete and schema hover.
            </span>
          </div>
          <button 
            onClick={() => setShowLspBanner(false)}
            className="p-1 hover:bg-trench rounded-sm text-textSecondary hover:text-textPrimary transition-colors animate-fade-in"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main split work space */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 min-h-0 overflow-y-auto">
        {/* Left pane: Monaco Editor & Progress status text */}
        <div className="lg:col-span-3 border-r border-border p-4 flex flex-col gap-4 min-h-[350px] lg:min-h-0">
          <div className="flex-1 flex flex-col border border-border">
            <div className="bg-trench/40 p-2 border-b border-border flex items-center gap-2 text-xs font-semibold text-textSecondary select-none">
              <Code2 size={14} className="text-ember" />
              <span>Query Input Workspace</span>
            </div>
            <div className="flex-1 min-h-0 relative h-[300px] lg:h-auto">
              <Suspense fallback={<SkeletonCard />}>
                <MonacoEditorComponent
                  value={query}
                  onChange={(val) => setQuery(val || "")}
                  onMount={(editor, monaco) => {
                    setEditorRef(editor);
                    setMonacoRef(monaco);
                  }}
                />
              </Suspense>
            </div>
          </div>

          {/* Error Message block */}
          {streamState.error && (
            <Card className="p-3 bg-cinder/10 border-cinder/30 flex items-center gap-2 text-xs font-semibold text-cinder">
              <span className="w-2 h-2 rounded-full bg-cinder animate-ping shrink-0" />
              <span>Error: {streamState.error}</span>
            </Card>
          )}

          {/* Status Message block */}
          {isAnalyzing && streamState.status?.stage && (
            <Card className="p-3 bg-trench/30 border-border/80 flex items-center gap-2 text-xs font-semibold text-textPrimary">
              <Activity size={14} className="text-glacier animate-pulse shrink-0" />
              <span>Stage [{streamState.status.stage.toUpperCase()}]: {streamState.status.message}</span>
            </Card>
          )}

          {/* PlanTreeVisualizer */}
          {streamState.plan && streamState.plan.plan_json && (
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider mb-1 block">
                Visualized Execution Plan Tree
              </span>
              <Suspense fallback={<SkeletonCard />}>
                <PlanTreeVisualizer planJson={streamState.plan.plan_json} />
              </Suspense>
            </div>
          )}

          {/* Optimization rewrite diff view */}
          {streamState.rewrite && (
            <DiffView
              originalSql={query}
              rewrittenSql={streamState.rewrite.rewritten_query}
              estimatedReduction={streamState.rewrite.estimated_row_reduction_percent}
              changes={streamState.rewrite.changes}
            />
          )}
        </div>

        {/* Right pane: Finding logs, Execution metrics, scorecards */}
        <div className="lg:col-span-2 p-4 flex flex-col gap-4 overflow-y-auto">
          {/* Cost Regression alert */}
          {streamState.regression && (
            <RegressionBanner
              previousCost={streamState.regression.previous_cost}
              currentCost={streamState.regression.current_cost}
              deltaPercent={streamState.regression.delta_percent}
            />
          )}

          {/* Performance scorecard conic ring summary */}
          {streamState.complete && (
            <Card className="p-4 border-border bg-trench/10 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block">
                  Analysis Pipeline Completed
                </span>
                <span className="text-[11px] text-textMuted mt-1 block">
                  Check ID: #{streamState.complete.query_id}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold text-textSecondary font-ui uppercase">Score shift:</span>
                <span 
                  className={`text-xs font-bold font-code px-2 py-0.5 rounded-sm border ${
                    streamState.complete.score_delta >= 0 
                      ? "text-glacier border-glacier/30 bg-glacier/5" 
                      : "text-cinder border-cinder/30 bg-cinder/5"
                  }`}
                >
                  {streamState.complete.score_delta >= 0 ? "+" : ""}
                  {streamState.complete.score_delta.toFixed(1)}
                </span>
              </div>
            </Card>
          )}

          {/* Execution Plan statistics summary */}
          {streamState.plan && (
            <Card className="p-4 border-border bg-pitch">
              <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5 mb-3">
                <Cpu size={15} className="text-ember" />
                <span>EXPLAIN Plan Diagnostics</span>
              </h3>
              <div className="grid grid-cols-2 gap-4 text-xs font-code">
                <div className="bg-abyss/40 p-2 border border-border/40 rounded-sm">
                  <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
                    Planner Cost
                  </span>
                  <span className="font-bold text-textPrimary">
                    {streamState.plan.total_cost.toFixed(2)}
                  </span>
                </div>
                <div className="bg-abyss/40 p-2 border border-border/40 rounded-sm">
                  <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
                    Cache Hit Ratio
                  </span>
                  <span className="font-bold text-glacier">
                    {(streamState.plan.cache_hit_ratio * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="bg-abyss/40 p-2 border border-border/40 rounded-sm">
                  <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
                    Sequential Scans
                  </span>
                  <span className={`font-bold ${streamState.plan.has_seq_scan ? "text-cinder" : "text-textPrimary"}`}>
                    {streamState.plan.has_seq_scan ? "PRESENT" : "ABSENT"}
                  </span>
                </div>
                <div className="bg-abyss/40 p-2 border border-border/40 rounded-sm">
                  <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
                    Temp Sort Spills
                  </span>
                  <span className={`font-bold ${streamState.plan.has_sort_spill ? "text-cinder" : "text-textPrimary"}`}>
                    {streamState.plan.has_sort_spill ? "DETECTED" : "NONE"}
                  </span>
                </div>
              </div>
            </Card>
          )}

          {/* Semantic Equivalence details */}
          <EquivalenceResult 
            equivalence={streamState.equivalence} 
            loading={isAnalyzing && streamState.status?.stage === "equivalence"}
          />

          {/* Index Recommendations DDL block */}
          {streamState.rewrite && streamState.rewrite.index_recommendations && (
            <IndexRecommendations recommendations={streamState.rewrite.index_recommendations} />
          )}

          {/* What-If Index Simulation Panel */}
          {selectedConnectionId && (
            <Card className="p-4 border-border bg-pitch">
              <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5 mb-3">
                <Play size={14} className="text-ember" />
                <span>What-If Index Simulation</span>
              </h3>
              
              <div className="flex flex-col gap-2.5">
                <span className="text-[10px] text-textSecondary leading-normal font-ui">
                  Simulate cost differences before creating indexes. Enter a CREATE INDEX statement below:
                </span>
                <input
                  type="text"
                  placeholder="CREATE INDEX idx_rental_customer ON rental (customer_id);"
                  value={indexStmt}
                  onChange={(e) => setIndexStmt(e.target.value)}
                  className="w-full bg-abyss border border-border px-3 py-1.5 text-xs text-textPrimary outline-none focus:border-ember rounded-sm font-code"
                />
                <button
                  onClick={handleSimulateWhatIf}
                  disabled={isSimulating || !indexStmt.trim()}
                  className="px-4 py-2 bg-ember hover:bg-ember/90 disabled:opacity-50 text-white text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center justify-center gap-1.5"
                >
                  {isSimulating ? "Simulating..." : "Simulate Index"}
                </button>
              </div>

              {whatIfResult && (
                <div className="mt-4 pt-3 border-t border-border/60">
                  {whatIfResult.success ? (
                    <div className="flex flex-col gap-2 font-ui">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-textSecondary">Simulated Index:</span>
                        <span className="font-bold text-glacier font-code">{whatIfResult.index_name}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs font-code mt-1">
                        <div className="bg-abyss/60 p-2 border border-border/40 rounded-sm">
                          <span className="block text-[9px] uppercase text-textSecondary font-ui">Original Cost</span>
                          <span className="font-bold text-textPrimary">{whatIfResult.original_cost?.toFixed(2)}</span>
                        </div>
                        <div className="bg-abyss/60 p-2 border border-border/40 rounded-sm">
                          <span className="block text-[9px] uppercase text-textSecondary font-ui">Simulated Cost</span>
                          <span className="font-bold text-glacier">{whatIfResult.hinted_cost?.toFixed(2)}</span>
                        </div>
                      </div>
                      
                      {whatIfResult.cost_reduction_percent !== undefined && (
                        <div className="text-center p-2 rounded-sm bg-glacier/10 border border-glacier/20 text-xs font-semibold text-glacier mt-1">
                          Estimated Cost Reduction: {whatIfResult.cost_reduction_percent}%
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-2 border border-cinder/30 bg-cinder/5 rounded-sm text-xs text-cinder leading-relaxed flex gap-2 items-start font-ui">
                      <AlertOctagon size={16} className="shrink-0 mt-0.5" />
                      <span>{whatIfResult.error}</span>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}

          {/* Static Rule Lint violations list */}
          <div className="flex flex-col gap-2">
            <h3 className="text-[10px] font-bold text-textSecondary uppercase tracking-wider mb-1">
              Static Rule Lint Findings ({streamState.findings.length})
            </h3>
            {streamState.findings.length > 0 ? (
              streamState.findings.map((f: any, idx: number) => (
                <FindingCard key={idx} finding={f} />
              ))
            ) : (
              <div className="text-center py-6 text-textMuted text-xs border border-dashed border-border/50 bg-trench/5">
                No static analysis violations detected yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
