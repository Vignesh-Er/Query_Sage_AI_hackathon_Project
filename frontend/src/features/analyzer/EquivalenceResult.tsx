import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import { Badge } from "../../design-system/components/Badge";
import { AlertTriangle, ShieldCheck } from "lucide-react";

interface EquivalenceData {
  original_row_count: number;
  optimized_row_count: number;
  original_hash: string;
  optimized_hash: string;
  result_match: boolean;
  notes?: string;
}

interface EquivalenceResultProps {
  equivalence?: EquivalenceData | null;
  loading?: boolean;
}

export const EquivalenceResult: React.FC<EquivalenceResultProps> = ({
  equivalence,
  loading = false
}) => {
  if (loading) {
    return (
      <Card className="p-4 border-border bg-trench/20 animate-pulse" style={{ fontFamily: TOKENS.fonts.ui }}>
        <div className="h-4 bg-vault w-1/4 rounded mb-2"></div>
        <div className="h-8 bg-vault w-full rounded"></div>
      </Card>
    );
  }

  if (!equivalence) return null;

  const isMatched = equivalence.result_match;

  return (
    <Card 
      className="p-4 border-border relative overflow-hidden"
      style={{ 
        fontFamily: TOKENS.fonts.ui,
        borderLeftWidth: "4px",
        borderLeftColor: isMatched ? TOKENS.colors.glacier : TOKENS.colors.cinder,
        backgroundColor: isMatched ? `${TOKENS.colors.glacier}08` : `${TOKENS.colors.cinder}08`
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isMatched ? (
            <ShieldCheck size={18} className="text-glacier" />
          ) : (
            <AlertTriangle size={18} className="text-cinder" />
          )}
          <span className="text-xs font-bold uppercase tracking-wider text-textPrimary">
            Semantic Equivalence Check
          </span>
        </div>
        <Badge variant={isMatched ? "glacier" : "cinder"}>
          {isMatched ? "VERIFIED EQUIVALENT" : "MUTATED RESULTS"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs">
        {/* Original Query Metrics */}
        <div className="bg-abyss/60 p-2.5 border border-border/40 rounded-sm">
          <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-semibold">
            Original Query Result
          </span>
          <div className="mt-1 flex items-center justify-between font-code">
            <span style={{ color: TOKENS.colors.text.primary }}>
              Rows: {equivalence.original_row_count}
            </span>
            <span className="text-[10px] text-textMuted max-w-[120px] truncate" title={equivalence.original_hash}>
              MD5: {equivalence.original_hash.substring(0, 10)}...
            </span>
          </div>
        </div>

        {/* Optimized Query Metrics */}
        <div className="bg-abyss/60 p-2.5 border border-border/40 rounded-sm">
          <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-semibold">
            Optimized Query Result
          </span>
          <div className="mt-1 flex items-center justify-between font-code">
            <span style={{ color: TOKENS.colors.text.primary }}>
              Rows: {equivalence.optimized_row_count}
            </span>
            <span className="text-[10px] text-textMuted max-w-[120px] truncate" title={equivalence.optimized_hash}>
              MD5: {equivalence.optimized_hash.substring(0, 10)}...
            </span>
          </div>
        </div>
      </div>

      <p className="mt-2.5 text-[10px] text-textSecondary leading-normal">
        {isMatched ? (
          "Dry-run execution verified that the optimized rewrite returns an identical row count and column checksum hash. The optimization is safe for release."
        ) : (
          equivalence.notes || "WARNING: The query output row count or column checksum returned from the database does not match the original query. Semantic alteration detected! Review rewrite rules before executing."
        )}
      </p>
    </Card>
  );
};
