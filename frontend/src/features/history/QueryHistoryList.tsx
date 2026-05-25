import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { QueryHistoryItem } from "./QueryHistoryItem";
import { ChevronLeft, ChevronRight } from "lucide-react";

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

interface QueryHistoryListProps {
  items: QueryItem[];
  onSelect: (item: QueryItem) => void;
  page: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
}

export const QueryHistoryList: React.FC<QueryHistoryListProps> = ({
  items,
  onSelect,
  page,
  totalPages,
  onPageChange
}) => {
  return (
    <div className="flex flex-col gap-2 h-full justify-between" style={{ fontFamily: TOKENS.fonts.ui }}>
      <div className="space-y-2 overflow-y-auto max-h-[400px] pr-1">
        {items.length > 0 ? (
          items.map((item) => (
            <QueryHistoryItem 
              key={item.id} 
              item={item} 
              onSelect={onSelect} 
            />
          ))
        ) : (
          <div className="text-center py-8 text-textSecondary text-xs border border-dashed border-border/50 bg-trench/10">
            No queries found matching the search criteria.
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border pt-3 mt-2 text-xs font-semibold text-textSecondary select-none">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(Math.max(1, page - 1))}
              disabled={page === 1}
              className="p-1 hover:bg-vault border border-border text-textSecondary hover:text-textPrimary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => onPageChange(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="p-1 hover:bg-vault border border-border text-textSecondary hover:text-textPrimary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
