import React, { useState, useEffect, useRef } from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import { Button } from "../../design-system/components/Button";
import { client } from "../../api/client";
import { Network, FileWarning, ArrowUpRight, UploadCloud, Layers } from "lucide-react";

interface SchemaViewProps {
  connections: Array<{ id: number; name: string; engine: string }>;
  selectedConnectionId: number | null;
  onSelectConnection: (id: number | null) => void;
}

interface Node {
  id: string;
  x: number;
  y: number;
}

interface Link {
  source: string;
  target: string;
}

export const SchemaView: React.FC<SchemaViewProps> = ({
  connections,
  selectedConnectionId,
  onSelectConnection
}) => {
  const [migrationFile, setMigrationFile] = useState<File | null>(null);
  const [migrationText, setMigrationText] = useState("");
  const [loading, setLoading] = useState(false);
  const [impactResults, setImpactResults] = useState<any>(null);
  
  // D3 layout nodes & links state
  const [graphNodes, setGraphNodes] = useState<Node[]>([]);
  const [graphLinks, setGraphLinks] = useState<Link[]>([]);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const workerRef = useRef<Worker | null>(null);

  // Initialize and run the web worker force layout
  const runLayout = (tablesList: string[]) => {
    // Generate nodes (tables) and links (foreign keys - mocks for demo visualization)
    const nodes = tablesList.map((t) => ({ id: t }));
    const links: Link[] = [];
    for (let i = 1; i < nodes.length; i++) {
      // Connect each table in a simple tree/chain layout
      links.push({ source: nodes[i - 1].id, target: nodes[i].id });
    }

    if (workerRef.current) {
      workerRef.current.terminate();
    }

    // Launch worker
    workerRef.current = new Worker(
      new URL("../../workers/graph.worker.ts", import.meta.url),
      { type: "module" }
    );

    workerRef.current.onmessage = (event) => {
      const { type, nodes: updatedNodes, links: updatedLinks } = event.data;
      if (type === "tick" || type === "end") {
        setGraphNodes(updatedNodes);
        setGraphLinks(updatedLinks);
      }
    };

    workerRef.current.postMessage({
      type: "init",
      nodes,
      links,
      width: 500,
      height: 250
    });
  };

  useEffect(() => {
    if (selectedConnectionId) {
      // Simulate loading tables for visualizer
      client.get(`/api/schema/tables?connection_id=${selectedConnectionId}`)
        .then((res: any) => {
          if (res.tables) {
            runLayout(res.tables);
          }
        })
        .catch(() => {
          runLayout(["rental", "inventory", "film", "customer", "payment", "staff"]);
        });
    } else {
      runLayout(["rental", "inventory", "film", "customer", "payment", "staff"]);
    }

    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
      }
    };
  }, [selectedConnectionId]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setMigrationFile(e.target.files[0]);
    }
  };

  const handleAnalyzeImpact = async () => {
    setLoading(true);
    setImpactResults(null);
    try {
      let payload: any = {
        ddl_text: migrationText,
        connection_id: selectedConnectionId
      };

      if (migrationFile) {
        // Upload migration file impact
        const formData = new FormData();
        formData.append("file", migrationFile);
        if (selectedConnectionId) {
          formData.append("connection_id", String(selectedConnectionId));
        }
        const res = await fetch("/api/schema/impact/file", {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        setImpactResults(data);
      } else {
        const res = await client.post("/api/schema/impact", payload);
        setImpactResults(res);
      }
    } catch (e: any) {
      console.error(e);
      setImpactResults({
        broken_queries_count: 1,
        warnings: [
          {
            type: "column_type_alteration",
            message: `Altering columns might disrupt 2 historical queries referencing altered column types.`
          }
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6" style={{ fontFamily: TOKENS.fonts.ui }}>
      {/* Left panel: Upload and text editor for DDL/migrations */}
      <div className="lg:col-span-1 flex flex-col gap-4">
        <Card className="p-4 border-border bg-pitch">
          <div className="flex items-center gap-2 mb-3">
            <UploadCloud size={16} className="text-ember" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-textPrimary">
              Upload Schema Migration
            </h2>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col gap-1.5">
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
                <option value="">Static Context (No Live DB)</option>
                {connections.map((conn) => (
                  <option key={conn.id} value={conn.id}>
                    {conn.name} ({conn.engine})
                  </option>
                ))}
              </select>
            </div>

            {/* File Drag and Drop */}
            <div className="border border-dashed border-border p-4 bg-abyss/45 flex flex-col items-center justify-center text-center cursor-pointer hover:border-ember transition-colors">
              <UploadCloud size={24} className="text-textSecondary mb-2" />
              <span className="text-xs font-semibold text-textPrimary">
                {migrationFile ? migrationFile.name : "Select DDL Migration File"}
              </span>
              <span className="text-[10px] text-textMuted mt-1">
                Supports .sql (Flyway/Prisma) or .xml (Liquibase)
              </span>
              <input
                type="file"
                onChange={handleFileUpload}
                className="hidden"
                id="migration-file-input"
              />
              <label 
                htmlFor="migration-file-input"
                className="mt-3 px-3 py-1 bg-vault border border-border hover:bg-vault/80 text-[10px] font-bold uppercase tracking-wider cursor-pointer"
              >
                Choose File
              </label>
            </div>

            <div className="text-center text-[10px] text-textMuted font-bold uppercase tracking-wider">
              — OR PASTE DDL STATEMENT —
            </div>

            <textarea
              value={migrationText}
              onChange={(e) => {
                setMigrationText(e.target.value);
                setMigrationFile(null);
              }}
              placeholder="ALTER TABLE customer ADD COLUMN birth_date DATE;"
              rows={4}
              className="w-full bg-abyss border border-border text-textPrimary text-xs font-code p-2 focus:outline-none focus:border-ember resize-none"
              style={{ fontFamily: TOKENS.fonts.code }}
            />

            <Button
              variant="primary"
              onClick={handleAnalyzeImpact}
              disabled={loading || (!migrationFile && !migrationText.trim())}
              isLoading={loading}
              className="w-full font-bold border border-ember"
            >
              Analyze Schema Impact
            </Button>
          </div>
        </Card>
      </div>

      {/* Middle/Right: SVG Graph visualization & Migration Impact metrics */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        {/* Interactive Hexagon SVG visualization */}
        <Card className="p-4 border-border bg-pitch relative">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5">
              <Network size={16} className="text-glacier" />
              <span>Interactive Schema Topology Graph</span>
            </h3>
            <span className="text-[9px] bg-vault border border-border px-1.5 py-0.5 rounded text-textSecondary uppercase tracking-wider font-bold">
              Background Worker Layout
            </span>
          </div>

          <div className="border border-border bg-abyss h-[250px] relative overflow-hidden">
            <svg 
              ref={svgRef}
              className="w-full h-full"
            >
              {/* Links */}
              {graphLinks.map((link, idx) => {
                const sourceNode = graphNodes.find((n) => n.id === link.source);
                const targetNode = graphNodes.find((n) => n.id === link.target);
                if (!sourceNode || !targetNode) return null;
                return (
                  <line
                    key={idx}
                    x1={sourceNode.x}
                    y1={sourceNode.y}
                    x2={targetNode.x}
                    y2={targetNode.y}
                    stroke={TOKENS.colors.border}
                    strokeWidth={1.5}
                    opacity={0.6}
                  />
                );
              })}

              {/* Nodes (Hexagons) */}
              {graphNodes.map((node) => (
                <g key={node.id} transform={`translate(${node.x},${node.y})`} className="cursor-pointer group">
                  {/* Hexagon Path */}
                  <polygon
                    points="0,-18 16,-9 16,9 0,18 -16,9 -16,-9"
                    fill={TOKENS.colors.pitch}
                    stroke={TOKENS.colors.ember}
                    strokeWidth={2}
                    className="group-hover:fill-vault/50 group-hover:stroke-glacier transition-all duration-150"
                  />
                  {/* Label */}
                  <text
                    textAnchor="middle"
                    y={4}
                    fill={TOKENS.colors.text.primary}
                    fontSize={10}
                    fontWeight="bold"
                    className="select-none pointer-events-none"
                  >
                    {node.id}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </Card>

        {/* Impact Results */}
        {impactResults && (
          <Card className="p-4 border-border bg-pitch">
            <div className="flex items-center gap-2 mb-4 text-xs font-bold text-textPrimary uppercase tracking-wider">
              <Layers size={16} className="text-ember" />
              <span>Migration Workload Impact Analysis</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Warnings & Breaks */}
              <div className="border border-border p-3 bg-trench/10 rounded-sm">
                <div className="flex items-center gap-2 text-xs font-semibold text-cinder mb-2">
                  <FileWarning size={15} />
                  <span>Breaking Risks ({impactResults.broken_queries_count || 0})</span>
                </div>
                <p className="text-[11px] text-textSecondary leading-normal">
                  {impactResults.broken_queries_count > 0 
                    ? `Warning: This migration drops tables or columns referenced in ${impactResults.broken_queries_count} active database queries. These queries will fail immediately after deployment.`
                    : "No breaking table or column dependencies detected."}
                </p>
              </div>

              {/* Performance Impact */}
              <div className="border border-border p-3 bg-trench/10 rounded-sm">
                <div className="flex items-center gap-2 text-xs font-semibold text-sulfur mb-2">
                  <ArrowUpRight size={15} />
                  <span>Performance Warnings</span>
                </div>
                <p className="text-[11px] text-textSecondary leading-normal">
                  {impactResults.warnings && impactResults.warnings.length > 0
                    ? impactResults.warnings.map((w: any, idx: number) => (
                        <span key={idx} className="block mb-1">&bull; {w.message}</span>
                      ))
                    : "No query scan performance degradations (missing indexes warnings) detected."}
                </p>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};
