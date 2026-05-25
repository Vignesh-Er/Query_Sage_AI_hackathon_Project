import React, { useState } from "react";
import { TOKENS } from "../tokens";
import { Copy, Check } from "lucide-react";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language = "sql"
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const blockStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.code,
    fontSize: "12px",
    backgroundColor: TOKENS.colors.abyss,
    border: `1px solid ${TOKENS.colors.border}`,
    borderRadius: TOKENS.radii.sm,
    padding: "12px",
    color: TOKENS.colors.text.primary,
    position: "relative",
    overflowX: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-all"
  };

  return (
    <div className="relative group">
      <pre style={blockStyles}>
        <code className={`language-${language}`}>{code}</code>
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-1.5 rounded opacity-0 group-hover:opacity-100 active:scale-95 transition-all"
        style={{
          backgroundColor: TOKENS.colors.trench,
          border: `1px solid ${TOKENS.colors.border}`,
          color: copied ? TOKENS.colors.glacier : TOKENS.colors.text.secondary
        }}
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  );
};
