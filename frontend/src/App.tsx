import React, { useState, useEffect } from "react";
import { AnalyzerView } from "./features/analyzer/AnalyzerView";
import { NaturalLanguageView } from "./features/natural-language/NaturalLanguageView";
import { SchemaView } from "./features/schema/SchemaView";
import { HistoryView } from "./features/history/HistoryView";
import { MetricDashboard } from "./features/metrics/MetricDashboard";
import { Drawer } from "./design-system/components/Drawer";
import { Button } from "./design-system/components/Button";
import { Input } from "./design-system/components/Input";
import { client } from "./api/client";
import { 
  Play, 
  Terminal, 
  History, 
  GitBranch, 
  Settings, 
  Plus, 
  Sparkles,
  Info,
  CheckCircle2,
  X,
  LineChart
} from "lucide-react";

interface ConnectionItem {
  id: number;
  name: string;
  engine: string;
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"analyzer" | "natural-language" | "schema" | "history" | "metrics">("analyzer");
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [customQuery, setCustomQuery] = useState("");

  // Drawers visibility
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAddConnectionOpen, setIsAddConnectionOpen] = useState(false);

  // Settings State
  const [aiProvider, setAiProvider] = useState("anthropic");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");
  const [ollamaHost, setOllamaHost] = useState("http://localhost:11434");
  const [ollamaModel, setOllamaModel] = useState("llama3");

  // New Connection Form
  const [newConnName, setNewConnName] = useState("");
  const [newConnEngine, setNewConnEngine] = useState("postgresql");
  const [newConnHost, setNewConnHost] = useState("127.0.0.1");
  const [newConnPort, setNewConnPort] = useState("5432");
  const [newConnDatabase, setNewConnDatabase] = useState("");
  const [newConnUsername, setNewConnUsername] = useState("");
  const [newConnPassword, setNewConnPassword] = useState("");
  const [testingConn, setTestingConn] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);

  // Fetch connections and settings on mount
  useEffect(() => {
    fetchConnections();
    fetchSettings();
  }, []);

  const fetchConnections = async () => {
    try {
      const res = await client.get("/api/connections");
      setConnections(res || []);
      if (res && res.length > 0 && !selectedConnectionId) {
        setSelectedConnectionId(res[0].id);
      }
    } catch (e) {
      console.error("Failed to load connections:", e);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await client.get("/api/settings");
      if (res) {
        // res is list of {key, value}
        res.forEach((item: any) => {
          if (item.key === "QUERYSAGE_AI_PROVIDER") setAiProvider(item.value);
          if (item.key === "QUERYSAGE_ANTHROPIC_API_KEY") setAnthropicApiKey(item.value);
          if (item.key === "QUERYSAGE_OLLAMA_HOST") setOllamaHost(item.value);
          if (item.key === "QUERYSAGE_OLLAMA_MODEL") setOllamaModel(item.value);
        });
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  };

  const handleSaveSettings = async () => {
    try {
      await client.patch("/api/settings/QUERYSAGE_AI_PROVIDER", { value: aiProvider });
      await client.patch("/api/settings/QUERYSAGE_ANTHROPIC_API_KEY", { value: anthropicApiKey });
      await client.patch("/api/settings/QUERYSAGE_OLLAMA_HOST", { value: ollamaHost });
      await client.patch("/api/settings/QUERYSAGE_OLLAMA_MODEL", { value: ollamaModel });
      setIsSettingsOpen(false);
    } catch (e) {
      alert("Failed to save settings: " + e);
    }
  };

  const handleTestConnection = async () => {
    setTestingConn(true);
    setTestResult(null);
    try {
      const res = await client.post("/api/connections/test", {
        engine: newConnEngine,
        host: newConnHost,
        port: parseInt(newConnPort),
        database: newConnDatabase,
        username: newConnUsername,
        password: newConnPassword
      });
      if (res.status === "success" || res.success) {
        setTestResult({ success: true, msg: "Connection successful!" });
      } else {
        setTestResult({ success: false, msg: res.message || "Connection failed." });
      }
    } catch (e: any) {
      setTestResult({ success: false, msg: e.message || "Failed to test connection." });
    } finally {
      setTestingConn(false);
    }
  };

  const handleAddConnection = async () => {
    try {
      await client.post("/api/connections", {
        name: newConnName,
        engine: newConnEngine,
        host: newConnHost,
        port: parseInt(newConnPort),
        database: newConnDatabase,
        username: newConnUsername,
        password: newConnPassword
      });
      fetchConnections();
      setIsAddConnectionOpen(false);
      // Reset form
      setNewConnName("");
      setNewConnDatabase("");
      setNewConnUsername("");
      setNewConnPassword("");
      setTestResult(null);
    } catch (e: any) {
      alert("Failed to create connection: " + (e.message || e));
    }
  };

  const handleLoadQueryIntoAnalyzer = (sql: string) => {
    setCustomQuery(sql);
    setActiveTab("analyzer");
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-abyss text-textPrimary overflow-hidden font-ui">
      {/* Top Premium Navbar */}
      <header 
        className="flex items-center justify-between px-6 py-3 border-b border-border bg-pitch/80 backdrop-blur-md select-none shrink-0"
      >
        {/* Brand Logo and Title */}
        <div className="flex items-center gap-2">
          <Terminal className="text-ember" size={20} />
          <h1 className="text-sm font-bold uppercase tracking-widest font-ui flex items-center gap-1.5">
            QuerySage
            <span className="text-[9px] bg-ember/15 text-ember px-1.5 py-0.5 border border-ember/20 font-code font-normal">
              v1.0.0
            </span>
          </h1>
        </div>

        {/* Tab Selection Navigation */}
        <nav className="flex items-center gap-1 bg-abyss p-0.5 border border-border/80 rounded-sm">
          <button
            onClick={() => setActiveTab("analyzer")}
            className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] uppercase font-bold tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "analyzer" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            <Play size={10} fill={activeTab === "analyzer" ? "currentColor" : "none"} />
            Analyzer
          </button>
          <button
            onClick={() => setActiveTab("natural-language")}
            className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] uppercase font-bold tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "natural-language" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            <Sparkles size={10} />
            AI Compiler
          </button>
          <button
            onClick={() => setActiveTab("schema")}
            className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] uppercase font-bold tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "schema" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            <GitBranch size={10} />
            Schema Evolution
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] uppercase font-bold tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "history" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            <History size={10} />
            History Audit
          </button>
          <button
            onClick={() => setActiveTab("metrics")}
            className={`flex items-center gap-1.5 px-4 py-1.5 text-[10px] uppercase font-bold tracking-wider rounded-sm transition-all duration-200 ${
              activeTab === "metrics" ? "bg-ember text-white" : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            <LineChart size={10} />
            Metrics
          </button>
        </nav>

        {/* Controls drawer buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAddConnectionOpen(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-trench/40 border border-border hover:bg-trench hover:text-white text-[10px] uppercase font-bold tracking-wider transition-all duration-150"
          >
            <Plus size={12} />
            Connection
          </button>
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 border border-border text-textSecondary hover:text-textPrimary hover:bg-vault/50 transition-colors"
            title="Configure settings"
          >
            <Settings size={14} />
          </button>
        </div>
      </header>

      {/* Main Content Workspace viewport */}
      <main className="flex-1 min-h-0 flex flex-col overflow-y-auto">
        {activeTab === "analyzer" && (
          <AnalyzerView
            initialQuery={customQuery}
            connections={connections}
            selectedConnectionId={selectedConnectionId}
            onSelectConnection={setSelectedConnectionId}
          />
        )}

        {activeTab === "natural-language" && (
          <NaturalLanguageView
            connections={connections}
            selectedConnectionId={selectedConnectionId}
            onSelectConnection={setSelectedConnectionId}
            onLoadIntoAnalyzer={handleLoadQueryIntoAnalyzer}
          />
        )}

        {activeTab === "schema" && (
          <SchemaView
            connections={connections}
            selectedConnectionId={selectedConnectionId}
            onSelectConnection={setSelectedConnectionId}
          />
        )}

        {activeTab === "history" && (
          <HistoryView
            onSelectQuery={handleLoadQueryIntoAnalyzer}
          />
        )}

        {activeTab === "metrics" && (
          <MetricDashboard
            selectedConnectionId={selectedConnectionId}
          />
        )}
      </main>

      {/* Connection management Drawer */}
      <Drawer
        isOpen={isAddConnectionOpen}
        onClose={() => setIsAddConnectionOpen(false)}
        title="Add Database Connection"
      >
        <div className="flex flex-col gap-4 text-xs font-ui">
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
              Connection name
            </label>
            <Input
              value={newConnName}
              onChange={(e) => setNewConnName(e.target.value)}
              placeholder="Postgres Localhost"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
              Engine type
            </label>
            <select
              value={newConnEngine}
              onChange={(e) => {
                setNewConnEngine(e.target.value);
                setNewConnPort(e.target.value === "mysql" ? "3306" : e.target.value === "sqlite" ? "" : "5432");
              }}
              className="bg-trench border border-border text-textPrimary text-xs px-2.5 py-1.5 focus:border-ember focus:outline-none rounded-none cursor-pointer w-full"
            >
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
            </select>
          </div>

          {newConnEngine !== "sqlite" ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2 flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                    Host Address
                  </label>
                  <Input
                    value={newConnHost}
                    onChange={(e) => setNewConnHost(e.target.value)}
                    placeholder="127.0.0.1"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                    Port
                  </label>
                  <Input
                    value={newConnPort}
                    onChange={(e) => setNewConnPort(e.target.value)}
                    placeholder="5432"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                  Database name
                </label>
                <Input
                  value={newConnDatabase}
                  onChange={(e) => setNewConnDatabase(e.target.value)}
                  placeholder="rental_db"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                    Username
                  </label>
                  <Input
                    value={newConnUsername}
                    onChange={(e) => setNewConnUsername(e.target.value)}
                    placeholder="postgres"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                    Password
                  </label>
                  <Input
                    type="password"
                    value={newConnPassword}
                    onChange={(e) => setNewConnPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                SQLite database filepath
              </label>
              <Input
                value={newConnDatabase}
                onChange={(e) => setNewConnDatabase(e.target.value)}
                placeholder="/users/home/.querysage/sqlite.db"
              />
            </div>
          )}

          {testResult && (
            <div 
              className={`p-3 border text-[11px] leading-relaxed flex items-start gap-2 ${
                testResult.success 
                  ? "bg-glacier/5 border-glacier text-textPrimary" 
                  : "bg-cinder/5 border-cinder text-textPrimary"
              }`}
            >
              {testResult.success ? (
                <CheckCircle2 size={16} className="text-glacier shrink-0 mt-0.5" />
              ) : (
                <X size={16} className="text-cinder shrink-0 mt-0.5" />
              )}
              <span>{testResult.msg}</span>
            </div>
          )}

          <div className="flex items-center gap-2 border-t border-border pt-4 mt-2">
            <Button
              variant="secondary"
              onClick={handleTestConnection}
              isLoading={testingConn}
              className="flex-1"
            >
              Test connection
            </Button>
            <Button
              variant="primary"
              onClick={handleAddConnection}
              disabled={!newConnName || testingConn}
              className="flex-1 border border-ember"
            >
              Save Connection
            </Button>
          </div>
        </div>
      </Drawer>

      {/* Settings management Drawer */}
      <Drawer
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        title="Settings & Credentials"
      >
        <div className="flex flex-col gap-4 text-xs font-ui">
          {/* AI Provider configuration selector */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
              AI Provider Model
            </label>
            <select
              value={aiProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              className="bg-trench border border-border text-textPrimary text-xs px-2.5 py-1.5 focus:border-ember focus:outline-none rounded-none cursor-pointer w-full"
            >
              <option value="anthropic">Anthropic (Claude API)</option>
              <option value="ollama">Ollama (Local Models)</option>
            </select>
          </div>

          {aiProvider === "anthropic" ? (
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                Anthropic API Key
              </label>
              <Input
                type="password"
                value={anthropicApiKey}
                onChange={(e) => setAnthropicApiKey(e.target.value)}
                placeholder="sk-ant-..."
              />
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                  Ollama host URL
                </label>
                <Input
                  value={ollamaHost}
                  onChange={(e) => setOllamaHost(e.target.value)}
                  placeholder="http://localhost:11434"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold tracking-wider text-textSecondary">
                  Ollama model name
                </label>
                <Input
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  placeholder="llama3"
                />
              </div>
            </>
          )}

          <div className="mt-2.5 text-[10px] text-textSecondary leading-normal bg-trench/15 p-2.5 border border-border rounded-sm flex items-start gap-1.5">
            <Info size={14} className="text-ember shrink-0 mt-0.5" />
            <span>
              Credentials and parameters are securely saved locally inside the SQLite settings table and retrieved on demand.
            </span>
          </div>

          <div className="flex items-center gap-2 border-t border-border pt-4 mt-2">
            <Button
              variant="secondary"
              onClick={() => setIsSettingsOpen(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveSettings}
              className="flex-1 border border-ember"
            >
              Save Settings
            </Button>
          </div>
        </div>
      </Drawer>
    </div>
  );
};
