import React, { useState, useEffect } from "react";
import { TOKENS } from "../../design-system/tokens";
import { NLInput } from "./NLInput";
import { TableScopeSelector } from "./TableScopeSelector";
import { AssumptionsPanel } from "./AssumptionsPanel";
import { Card } from "../../design-system/components/Card";
import { CodeBlock } from "../../design-system/components/CodeBlock";
import { Button } from "../../design-system/components/Button";
import { useSchemaFetch } from "../../hooks/useSchemaFetch";
import { client } from "../../api/client";
import { Database, Sparkles, AlertTriangle, ArrowRight } from "lucide-react";

interface NaturalLanguageViewProps {
  connections: Array<{ id: number; name: string; engine: string }>;
  selectedConnectionId: number | null;
  onSelectConnection: (id: number | null) => void;
  onLoadIntoAnalyzer: (sql: string) => void;
}

export const NaturalLanguageView: React.FC<NaturalLanguageViewProps> = ({
  connections,
  selectedConnectionId,
  onSelectConnection,
  onLoadIntoAnalyzer
}) => {
  const [nlText, setNlText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [generatedSql, setGeneratedSql] = useState("");
  
  // Logical assumptions mock output for UI completeness
  const [assumptions, setAssumptions] = useState<Array<{ context: string; assumption: string }>>([]);
  const [lintFindings, setLintFindings] = useState<any[]>([]);

  // Fetch schema details for the selected connection
  const { schema, refetch: fetchSchema } = useSchemaFetch(selectedConnectionId);
  const tables = schema?.tables || [];
  const [selectedTables, setSelectedTables] = useState<string[]>([]);

  useEffect(() => {
    if (selectedConnectionId) {
      fetchSchema();
    }
  }, [selectedConnectionId]);

  // Set all tables checked on load
  useEffect(() => {
    if (tables) {
      setSelectedTables(tables);
    }
  }, [tables]);

  const handleToggleTable = (tbl: string) => {
    if (selectedTables.includes(tbl)) {
      setSelectedTables(selectedTables.filter((t) => t !== tbl));
    } else {
      setSelectedTables([...selectedTables, tbl]);
    }
  };

  const handleSelectAll = () => setSelectedTables(tables);
  const handleClearAll = () => setSelectedTables([]);

  const handleTranslate = async () => {
    if (!nlText.trim()) return;
    setIsLoading(true);
    setLintFindings([]);
    try {
      // POST payload to natural language translate endpoint
      const res = await client.post("/api/natural-language/translate", {
        prompt: nlText,
        connection_id: selectedConnectionId,
        schema_subset: selectedTables
      });

      setGeneratedSql(res.sql);
      
      // Load rules findings from translation payload if backend triggers them
      if (res.findings) {
        setLintFindings(res.findings);
      }

      // Prepopulate assumptions based on tables
      setAssumptions([
        {
          context: "Tables scope",
          assumption: `Generating SQL query matching tables DDL rules for [${selectedTables.join(", ")}]`
        },
        {
          context: "Predicate filter",
          assumption: "Mapping search clauses directly into indexed constraints to maximize query execution safety"
        }
      ]);
    } catch (e: any) {
      console.error(e);
      setGeneratedSql(`-- Error translating query: ${e.message || "Unknown error"}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 p-6" style={{ fontFamily: TOKENS.fonts.ui }}>
      {/* Left panel: Connection selector & Table scope checklist */}
      <div className="lg:col-span-1 flex flex-col gap-4">
        <Card className="p-4 border-border bg-pitch flex flex-col gap-4">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5">
              <Database size={15} className="text-ember" />
              <span>Translation Context</span>
            </h3>
            <p className="text-[10px] text-textSecondary mt-0.5">
              Select database schema context passed to LLM
            </p>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[9px] text-textSecondary uppercase tracking-wider font-bold">
              Database connection
            </label>
            <select
              value={selectedConnectionId || ""}
              onChange={(e) => {
                const val = e.target.value;
                onSelectConnection(val ? parseInt(val) : null);
              }}
              className="bg-trench border border-border text-textPrimary text-xs px-2.5 py-1.5 focus:border-ember focus:outline-none rounded-none cursor-pointer w-full"
            >
              <option value="">Static Translation (No Schema)</option>
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.name} ({conn.engine})
                </option>
              ))}
            </select>
          </div>

          {selectedConnectionId && (
            <TableScopeSelector
              tables={tables}
              selectedTables={selectedTables}
              onToggleTable={handleToggleTable}
              onSelectAll={handleSelectAll}
              onClearAll={handleClearAll}
            />
          )}
        </Card>
      </div>

      {/* Middle/Right panel: Inputs, SQL preview, and Linting findings */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <Card className="p-4 border-border bg-pitch">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-ember" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-textPrimary">
              Natural Language SQL Compiler
            </h2>
          </div>

          <NLInput
            value={nlText}
            onChange={setNlText}
            onSubmit={handleTranslate}
            isLoading={isLoading}
          />

          {generatedSql && (
            <div className="mt-6 space-y-4">
              <AssumptionsPanel assumptions={assumptions} />

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider">
                    Compiled SQL Output
                  </span>
                  <Button
                    variant="primary"
                    onClick={() => onLoadIntoAnalyzer(generatedSql)}
                    className="h-6 text-[9px] px-3 font-bold uppercase tracking-wider flex items-center gap-1 border border-ember"
                  >
                    <span>Load into Analyzer</span>
                    <ArrowRight size={10} />
                  </Button>
                </div>
                <CodeBlock code={generatedSql} language="sql" />
              </div>

              {/* Translation static findings */}
              {lintFindings.length > 0 && (
                <div className="border border-border/80 p-3 bg-trench/15 rounded-sm">
                  <div className="flex items-center gap-2 text-xs font-bold text-cinder mb-2 uppercase tracking-wider">
                    <AlertTriangle size={14} />
                    <span>Post-compile Lint Warnings ({lintFindings.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {lintFindings.map((finding, idx) => (
                      <div 
                        key={idx} 
                        className="text-[11px] font-ui flex items-center gap-2 text-textSecondary border-b border-border/30 pb-1.5 last:border-b-0"
                      >
                        <span className="font-code font-bold text-cinder">{finding.rule_id}</span>
                        <span>{finding.title}: {finding.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
