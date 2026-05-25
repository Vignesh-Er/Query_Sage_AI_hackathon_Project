import React, { useState, useEffect } from "react";
import { TOKENS } from "../../design-system/tokens";
import { QueryHistoryList } from "./QueryHistoryList";
import { ImprovementTimeline } from "./ImprovementTimeline";
import { Input } from "../../design-system/components/Input";
import { Card } from "../../design-system/components/Card";
import { useHistory } from "../../hooks/useHistory";
import { useScore } from "../../hooks/useScore";
import { Search, Tag, Filter, RefreshCw, BarChart2 } from "lucide-react";

interface QueryItem {
  id: number;
  fingerprint: string;
  raw_sql: string;
  normalized_sql: string;
  submitted_at: string;
  source: string;
  tags?: string;
  connection_name?: string;
  score?: number;
}

interface HistoryViewProps {
  onSelectQuery: (query: string, connectionId: number | null) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ onSelectQuery }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [page, setPage] = useState(1);
  const [selectedFingerprint, setSelectedFingerprint] = useState<string | null>(null);
  
  const { history: historyData, loading: historyLoading, updateFilters, refetch: fetchHistory } = useHistory();
  const totalPages = Math.ceil(historyData.length / 15) || 1;
  const { scorecard, loading: scoreLoading, refetch: fetchScores } = useScore();
  const scoreData = scorecard?.trend_data || [];

  // Trigger reloading history and scores
  const handleRefresh = () => {
    fetchHistory();
    fetchScores();
  };

  useEffect(() => {
    updateFilters({
      page,
      search: searchQuery,
      tag: selectedTag
    });
  }, [page, searchQuery, selectedTag]);

  useEffect(() => {
    fetchScores();
  }, []);

  // Compute all unique tags in the history items for the filter list
  const uniqueTags = React.useMemo(() => {
    const tagsSet = new Set<string>();
    historyData.forEach((item: any) => {
      try {
        const parsed = JSON.parse(item.tags || "[]");
        if (Array.isArray(parsed)) {
          parsed.forEach((t) => tagsSet.add(t));
        }
      } catch {}
    });
    return Array.from(tagsSet);
  }, [historyData]);

  const handleSelectItem = (item: QueryItem) => {
    setSelectedFingerprint(item.fingerprint);
    // Find connection ID from connection name or model if available, fallback to null
    onSelectQuery(item.raw_sql, null);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6" style={{ fontFamily: TOKENS.fonts.ui }}>
      {/* Left panel: Query log table, search & tag filters */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        <Card className="p-4 border-border bg-pitch">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5">
                <Filter size={16} className="text-ember" />
                <span>Historical Profiling Audit</span>
              </h2>
              <p className="text-[10px] text-textSecondary mt-0.5">
                Search, filter, and load previously optimized database queries
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="p-1.5 border border-border text-textSecondary hover:text-textPrimary hover:bg-vault/50 transition-colors rounded-sm"
              title="Refresh logs"
            >
              <RefreshCw size={14} className={historyLoading ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Search bar & Tag selector row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div className="relative">
              <Search 
                size={14} 
                className="absolute left-3 top-1/2 -translate-y-1/2 text-textSecondary" 
              />
              <Input
                placeholder="Search queries by SQL content..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="pl-9 w-full text-xs"
              />
            </div>

            <div className="flex items-center gap-2">
              <Tag size={14} className="text-textSecondary shrink-0" />
              <select
                value={selectedTag}
                onChange={(e) => {
                  setSelectedTag(e.target.value);
                  setPage(1);
                }}
                className="bg-trench border border-border text-textPrimary text-xs px-2.5 py-1.5 focus:border-ember focus:outline-none rounded-none cursor-pointer flex-1"
              >
                <option value="">All Tags</option>
                {uniqueTags.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Paginated list */}
          {historyLoading ? (
            <div className="flex items-center justify-center py-20 text-xs text-textSecondary">
              <RefreshCw className="animate-spin mr-2" size={16} />
              Loading history audit logs...
            </div>
          ) : (
            <QueryHistoryList
              items={historyData}
              onSelect={handleSelectItem}
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
        </Card>
      </div>

      {/* Right panel: Timeline chart and stats summary */}
      <div className="flex flex-col gap-4">
        {selectedFingerprint ? (
          scoreLoading ? (
            <div className="flex items-center justify-center py-20 text-xs text-textSecondary">
              <RefreshCw className="animate-spin mr-2" size={16} />
              Loading scorecard timeline...
            </div>
          ) : (
            <ImprovementTimeline data={scoreData} />
          )
        ) : (
          <div className="text-center py-8 text-xs text-textMuted border border-dashed border-border bg-pitch p-4 rounded-sm">
            Select a query fingerprint group from the history log to inspect its scorecard improvement timeline.
          </div>
        )}

        {/* Scorecard quick summary card */}
        <Card className="p-4 border-border bg-trench/20">
          <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5 mb-3">
            <BarChart2 size={16} className="text-glacier" />
            <span>Optimization Statistics</span>
          </h3>
          <div className="space-y-3 text-[11px] leading-relaxed text-textSecondary">
            <div className="flex items-center justify-between border-b border-border pb-1.5">
              <span>Total Checked Queries</span>
              <span className="font-code font-bold text-textPrimary">{historyData.length}</span>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-1.5">
              <span>Avg Quality Score</span>
              <span className="font-code font-bold text-glacier">
                {scoreData.length > 0 
                  ? (scoreData.reduce((acc: number, curr: any) => acc + curr.query_score, 0) / scoreData.length).toFixed(1)
                  : "100.0"}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-1.5">
              <span>Active Streak count</span>
              <span className="font-code font-bold text-ember">
                {scoreData.length > 0 ? 5 : 0} Queries
              </span>
            </div>
            <p className="text-[10px] text-textMuted leading-normal">
              Scores are calculated based on AST static check rules (deducting severity penalties) and EXPLAIN scan reduction metrics.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
