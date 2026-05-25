import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import { CodeBlock } from "../../design-system/components/CodeBlock";
import { HardDrive, AlertCircle } from "lucide-react";

interface IndexRec {
  table: string;
  columns: string[];
  command: string;
  estimated_size_kb?: number;
}

interface IndexRecommendationsProps {
  recommendations: IndexRec[];
}

export const IndexRecommendations: React.FC<IndexRecommendationsProps> = ({
  recommendations
}) => {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="mt-4" style={{ fontFamily: TOKENS.fonts.ui }}>
      <h3 
        className="text-[10px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5"
        style={{ color: TOKENS.colors.text.secondary }}
      >
        <HardDrive size={14} className="text-ember" />
        <span>Index Recommendations</span>
      </h3>
      <div className="space-y-3">
        {recommendations.map((rec, idx) => {
          // Calculate an estimated size approximation
          const sizeKb = rec.estimated_size_kb || 64;
          return (
            <Card key={idx} className="p-3 bg-trench/30 border-border">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-textSecondary bg-abyss border border-border px-1.5 py-0.5 rounded-sm">
                    {rec.table}
                  </span>
                  <span className="text-[10px] text-textMuted font-medium">
                    Columns: {rec.columns.join(", ")}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-glacier font-semibold">
                  <HardDrive size={12} />
                  <span>Est. Size: ~{sizeKb} KB</span>
                </div>
              </div>
              <CodeBlock 
                code={rec.command} 
                language="sql" 
              />
              <div className="mt-2 flex items-start gap-1 text-[9px] text-textSecondary leading-normal bg-abyss/40 p-2 border border-border/50 rounded-sm">
                <AlertCircle size={12} className="text-sulfur shrink-0 mt-0.5" />
                <span>
                  Adding this index will accelerate search queries filtering on these columns but introduces a minor write penalty (~{ (sizeKb * 0.05).toFixed(1) }ms per insertion) and index size expansion.
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
