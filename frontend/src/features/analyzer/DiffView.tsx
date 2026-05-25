import React, { useState } from "react";
import { TOKENS } from "../../design-system/tokens";
import { DiffEditor, loader } from "@monaco-editor/react";
import { MONACO_THEME } from "../../design-system/monaco-theme";
import { Sparkles, TrendingDown } from "lucide-react";

// Register custom Monaco Theme
loader.init().then((monaco) => {
  monaco.editor.defineTheme("querysage-theme", MONACO_THEME as any);
});

interface DiffViewProps {
  originalSql: string;
  rewrittenSql: string;
  estimatedReduction: number;
  changes: Array<{
    type: string;
    original_fragment: string;
    replacement_fragment: string;
    reason: string;
    orm_equivalent?: string;
  }>;
  ormRewrites?: {
    prisma?: string;
    sequelize?: string;
    typeorm?: string;
  };
}

export const DiffView: React.FC<DiffViewProps> = ({
  originalSql,
  rewrittenSql,
  estimatedReduction,
  changes,
  ormRewrites
}) => {
  const [activeTab, setActiveTab] = useState<"sql" | "orm">("sql");
  const [selectedOrm, setSelectedOrm] = useState<"prisma" | "sequelize" | "typeorm">("prisma");

  const hasOrmEquivalent = !!ormRewrites || (changes && changes.some(c => c.orm_equivalent));

  const getOrmCode = () => {
    if (ormRewrites) {
      const ormKey = selectedOrm as keyof typeof ormRewrites;
      return { 
        original: "// Original Query", 
        modified: ormRewrites[ormKey] || ormRewrites.prisma || "" 
      };
    }
    const items = changes ? changes.filter(c => c.orm_equivalent) : [];
    if (items.length > 0) {
      return {
        original: "// Original SQL Fragments:\n" + items.map(c => c.original_fragment).join("\n\n"),
        modified: `// Equivalent ORM Rewrites:\n` + items.map(c => `// Reason: ${c.reason}\n${c.orm_equivalent}`).join("\n\n")
      };
    }
    return { original: "", modified: "" };
  };

  const ormCode = getOrmCode();

  return (
    <div 
      className="border border-border bg-pitch flex flex-col h-[500px]"
      style={{ fontFamily: TOKENS.fonts.ui }}
    >
      {/* Top Banner: Reduction Metrics & Tabs */}
      <div className="flex items-center justify-between border-b border-border p-3 bg-trench/50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-textPrimary">
            <Sparkles size={16} className="text-ember" />
            <span>AI Code Optimization Rewrite</span>
          </div>
          {estimatedReduction > 0 && (
            <div 
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold"
              style={{
                backgroundColor: `${TOKENS.colors.glacier}15`,
                color: TOKENS.colors.glacier
               }}
            >
              <TrendingDown size={12} />
              <span>-{estimatedReduction.toFixed(0)}% Row Scan Reduction</span>
            </div>
          )}
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-1 bg-abyss p-0.5 border border-border rounded-sm">
          <button
            onClick={() => setActiveTab("sql")}
            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "sql" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            SQL Diff
          </button>
          {hasOrmEquivalent && (
            <button
              onClick={() => setActiveTab("orm")}
              className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-all duration-200 ${
                activeTab === "orm" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
              }`}
            >
              ORM Translation
            </button>
          )}
        </div>
      </div>

      {/* Main Diff Editor */}
      <div className="flex-1 min-h-0 relative">
        {activeTab === "sql" ? (
          <DiffEditor
            original={originalSql}
            modified={rewrittenSql}
            language="sql"
            theme="querysage-theme"
            options={{
              readOnly: true,
              domReadOnly: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbersMinChars: 3,
              renderSideBySide: true,
              fontSize: 12,
              fontFamily: TOKENS.fonts.code
            }}
          />
        ) : (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 p-2 border-b border-border bg-pitch/80 text-[10px] font-semibold text-textSecondary">
              <button 
                onClick={() => setSelectedOrm("prisma")}
                className={`px-2 py-0.5 rounded ${selectedOrm === "prisma" ? "bg-vault text-textPrimary" : "hover:text-textPrimary"}`}
              >
                Prisma
              </button>
              <button 
                onClick={() => setSelectedOrm("sequelize")}
                className={`px-2 py-0.5 rounded ${selectedOrm === "sequelize" ? "bg-vault text-textPrimary" : "hover:text-textPrimary"}`}
              >
                Sequelize
              </button>
              <button 
                onClick={() => setSelectedOrm("typeorm")}
                className={`px-2 py-0.5 rounded ${selectedOrm === "typeorm" ? "bg-vault text-textPrimary" : "hover:text-textPrimary"}`}
              >
                TypeORM
              </button>
            </div>
            <div className="flex-1">
              <DiffEditor
                original={ormCode.original}
                modified={ormCode.modified}
                language="typescript"
                theme="querysage-theme"
                options={{
                  readOnly: true,
                  domReadOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  renderSideBySide: true,
                  fontSize: 11,
                  fontFamily: TOKENS.fonts.code
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Bottom Panel: Specific Changes List */}
      {changes && changes.length > 0 && (
        <div className="border-t border-border p-3 bg-trench/20 overflow-y-auto max-h-[140px] text-xs">
          <span className="block text-[10px] font-bold text-textSecondary uppercase tracking-wider mb-2 font-ui">
            Rewrites Breakdown
          </span>
          <div className="space-y-2">
            {changes.map((change, idx) => (
              <div 
                key={idx} 
                className="border border-border p-2 bg-abyss/40 text-[11px] font-ui leading-relaxed rounded-sm"
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-ember uppercase text-[9px] tracking-wider font-bold">
                    {change.type.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                  <code className="bg-cinder/10 text-cinder px-1 font-code text-[10px] rounded-sm truncate max-w-[200px]">
                    {change.original_fragment}
                  </code>
                  <span className="text-textMuted">&rarr;</span>
                  <code className="bg-glacier/10 text-glacier px-1 font-code text-[10px] rounded-sm truncate max-w-[200px]">
                    {change.replacement_fragment}
                  </code>
                </div>
                <p className="text-textSecondary mt-1 text-[10px]">{change.reason}</p>
                {change.orm_equivalent && (
                  <div className="mt-2 bg-vault/40 border-l border-ember p-1.5 rounded-sm">
                    <span className="text-[9px] font-bold text-ember uppercase tracking-wider block">ORM Equivalent</span>
                    <code className="text-textPrimary font-code text-[10px] whitespace-pre-wrap block mt-0.5">{change.orm_equivalent}</code>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
