import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Button } from "../../design-system/components/Button";
import { Play, Database, CheckSquare, Eye, RefreshCw } from "lucide-react";

interface ConnectionItem {
  id: number;
  name: string;
  engine: string;
}

interface ToolbarStripProps {
  connections: ConnectionItem[];
  selectedConnectionId: number | null;
  onSelectConnection: (id: number | null) => void;
  includePlan: boolean;
  onToggleIncludePlan: (val: boolean) => void;
  verifyEquivalence: boolean;
  onToggleVerifyEquivalence: (val: boolean) => void;
  onFormat: () => void;
  onClear: () => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
}

export const ToolbarStrip: React.FC<ToolbarStripProps> = ({
  connections,
  selectedConnectionId,
  onSelectConnection,
  includePlan,
  onToggleIncludePlan,
  verifyEquivalence,
  onToggleVerifyEquivalence,
  onFormat,
  onClear,
  onAnalyze,
  isAnalyzing
}) => {
  return (
    <div 
      className="p-3 border-b border-border bg-pitch/80 flex items-center justify-between gap-4 flex-wrap"
      style={{ fontFamily: TOKENS.fonts.ui }}
    >
      <div className="flex items-center gap-4 flex-wrap">
        {/* Connection Selector */}
        <div className="flex items-center gap-2">
          <Database size={14} style={{ color: TOKENS.colors.text.secondary }} />
          <select
            value={selectedConnectionId || ""}
            onChange={(e) => {
              const val = e.target.value;
              onSelectConnection(val ? parseInt(val) : null);
            }}
            className="bg-trench border border-border text-textPrimary text-xs px-2.5 py-1 focus:border-ember focus:outline-none rounded-none cursor-pointer"
          >
            <option value="">Static Mode (AST Only)</option>
            {connections.map((conn) => (
              <option key={conn.id} value={conn.id}>
                {conn.name} ({conn.engine})
              </option>
            ))}
          </select>
        </div>

        {/* Feature Switches */}
        {selectedConnectionId && (
          <div className="flex items-center gap-4 text-xs font-semibold text-textSecondary select-none">
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-textPrimary transition-colors">
              <input
                type="checkbox"
                checked={includePlan}
                onChange={(e) => onToggleIncludePlan(e.target.checked)}
                className="accent-ember w-3.5 h-3.5 cursor-pointer"
              />
              <span className="flex items-center gap-1">
                <Eye size={12} />
                EXPLAIN Plan
              </span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer hover:text-textPrimary transition-colors">
              <input
                type="checkbox"
                checked={verifyEquivalence}
                onChange={(e) => onToggleVerifyEquivalence(e.target.checked)}
                className="accent-ember w-3.5 h-3.5 cursor-pointer"
              />
              <span className="flex items-center gap-1">
                <CheckSquare size={12} />
                Equivalence Test
              </span>
            </label>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onFormat}
          className="px-3 py-1.5 border border-border text-textSecondary hover:text-textPrimary hover:bg-vault/50 text-[10px] uppercase font-bold tracking-wider transition-all duration-200"
        >
          Format
        </button>
        <button
          onClick={onClear}
          className="px-3 py-1.5 border border-border text-textSecondary hover:text-textPrimary hover:bg-vault/50 text-[10px] uppercase font-bold tracking-wider transition-all duration-200"
        >
          Clear
        </button>

        <Button
          variant="primary"
          onClick={onAnalyze}
          isLoading={isAnalyzing}
          className="font-bold border border-ember"
        >
          {isAnalyzing ? (
            <span className="flex items-center gap-1">
              <RefreshCw size={12} className="animate-spin mr-1" />
              Profiling...
            </span>
          ) : (
            <span className="flex items-center gap-1.5">
              <Play size={12} fill="currentColor" />
              Run Profile
            </span>
          )}
        </Button>
      </div>
    </div>
  );
};
