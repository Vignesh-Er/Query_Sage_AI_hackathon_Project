import React from "react";
import { TOKENS } from "../../design-system/tokens";




interface TableScopeSelectorProps {
  tables: string[];
  selectedTables: string[];
  onToggleTable: (tableName: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
}

export const TableScopeSelector: React.FC<TableScopeSelectorProps> = ({
  tables,
  selectedTables,
  onToggleTable,
  onSelectAll,
  onClearAll
}) => {
  if (tables.length === 0) {
    return (
      <div className="p-4 border border-dashed border-border/50 text-textSecondary text-[11px] text-center font-ui">
        No schema tables loaded. Select a database connection first.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 h-full" style={{ fontFamily: TOKENS.fonts.ui }}>
      <div className="flex items-center justify-between border-b border-border pb-2 mb-1">
        <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider">
          Schema Context Scope ({selectedTables.length}/{tables.length})
        </span>
        <div className="flex items-center gap-2 text-[9px] uppercase tracking-wider font-bold">
          <button 
            onClick={onSelectAll}
            className="text-glacier hover:text-ember transition-colors"
          >
            All
          </button>
          <span className="text-textMuted">|</span>
          <button 
            onClick={onClearAll}
            className="text-textSecondary hover:text-ember transition-colors"
          >
            None
          </button>
        </div>
      </div>

      <div className="space-y-1.5 overflow-y-auto max-h-[160px] pr-1">
        {tables.map((table) => {
          const isChecked = selectedTables.includes(table);
          return (
            <label
              key={table}
              className="flex items-center gap-2 px-2.5 py-1.5 border border-border/40 hover:border-border hover:bg-vault/20 cursor-pointer select-none transition-colors rounded-none"
              style={{
                backgroundColor: isChecked ? `${TOKENS.colors.ember}05` : "transparent",
              }}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggleTable(table)}
                className="accent-ember w-3.5 h-3.5 cursor-pointer"
              />
              <span className="text-xs font-code text-textPrimary truncate" style={{ fontFamily: TOKENS.fonts.code }}>
                {table}
              </span>
            </label>
          );
        })}
      </div>
      <p className="text-[9px] text-textMuted leading-normal mt-1">
        Limits the table DDL context sent to the AI engine to minimize tokens and improve SQL translation accuracy.
      </p>
    </div>
  );
};
