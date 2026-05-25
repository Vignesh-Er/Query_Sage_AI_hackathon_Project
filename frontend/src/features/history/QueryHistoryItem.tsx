import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Calendar, PlayCircle, Tag } from "lucide-react";

interface QueryItem {
  id: number;
  fingerprint: string;
  raw_sql: string;
  normalized_sql: string;
  submitted_at: string;
  source: string;
  tags?: string; // stringified JSON
  connection_name?: string;
  score?: number;
}

interface QueryHistoryItemProps {
  item: QueryItem;
  onSelect: (item: QueryItem) => void;
}

export const QueryHistoryItem: React.FC<QueryHistoryItemProps> = ({ item, onSelect }) => {
  const score = item.score !== undefined ? item.score : 100;
  
  const getScoreColor = (sc: number) => {
    if (sc >= 90) return TOKENS.colors.glacier;
    if (sc >= 75) return TOKENS.colors.sulfur;
    return TOKENS.colors.cinder;
  };

  const parsedTags: string[] = React.useMemo(() => {
    try {
      return JSON.parse(item.tags || "[]");
    } catch {
      return [];
    }
  }, [item.tags]);

  return (
    <div 
      onClick={() => onSelect(item)}
      className="p-3 border border-border/60 bg-trench/20 hover:bg-trench/60 flex items-center justify-between gap-4 cursor-pointer transition-all duration-150 group"
      style={{ fontFamily: TOKENS.fonts.ui }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Connection & Timestamp badges */}
          <span 
            className="text-[9px] uppercase tracking-wider font-bold"
            style={{ color: TOKENS.colors.text.secondary }}
          >
            {item.connection_name || "LOCAL FILE"}
          </span>
          <span className="text-textMuted text-[9px] flex items-center gap-1">
            <Calendar size={10} />
            {new Date(item.submitted_at).toLocaleString()}
          </span>
          
          {parsedTags.map((tag, idx) => (
            <span 
              key={idx} 
              className="text-[8px] bg-vault/50 text-textSecondary border border-border px-1 rounded-sm uppercase tracking-wider flex items-center gap-0.5"
            >
              <Tag size={8} />
              {tag}
            </span>
          ))}
        </div>

        {/* Truncated SQL preview */}
        <div 
          className="text-xs font-code mt-1.5 truncate text-textPrimary group-hover:text-ember transition-colors"
          style={{ fontFamily: TOKENS.fonts.code }}
        >
          {item.raw_sql}
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {/* Score Ring / Bubble */}
        <div 
          className="w-8 h-8 rounded-full border flex flex-col items-center justify-center"
          style={{ 
            borderColor: `${getScoreColor(score)}40`,
            color: getScoreColor(score),
            backgroundColor: `${getScoreColor(score)}0D`
          }}
        >
          <span className="text-[11px] font-bold font-code leading-none">
            {score.toFixed(0)}
          </span>
        </div>
        
        <PlayCircle 
          size={18} 
          className="text-textMuted group-hover:text-ember transition-colors" 
        />
      </div>
    </div>
  );
};
