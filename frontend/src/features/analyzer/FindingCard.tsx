import React, { useState } from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import { Badge } from "../../design-system/components/Badge";
import { ChevronDown, ChevronUp } from "lucide-react";

interface FindingData {
  rule_id: string;
  severity: number;
  category: string;
  title: string;
  description: string;
  location_start?: number | null;
  location_end?: number | null;
  auto_fixable?: boolean;
}

interface FindingCardProps {
  finding: FindingData;
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding }) => {
  const [isOpen, setIsOpen] = useState(false);

  const getSeverityColor = (sev: number) => {
    if (sev >= 8) return TOKENS.colors.cinder;
    if (sev >= 5) return TOKENS.colors.sulfur;
    return TOKENS.colors.glacier;
  };

  const severityColor = getSeverityColor(finding.severity);

  return (
    <Card 
      severity={finding.severity}
      className="mb-3 overflow-hidden transition-all duration-200"
    >
      <div 
        className="flex items-center justify-between p-4 cursor-pointer select-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          <div 
            className="flex items-center justify-center w-6 h-6 rounded-sm border"
            style={{ 
              borderColor: severityColor,
              color: severityColor,
              backgroundColor: `${severityColor}10`
            }}
          >
            <span className="text-[10px] font-bold">{finding.severity}</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span 
                className="text-[10px] font-bold uppercase tracking-wider font-ui"
                style={{ color: TOKENS.colors.text.secondary }}
              >
                {finding.rule_id}
              </span>
              <Badge variant={finding.severity >= 8 ? "cinder" : finding.severity >= 5 ? "sulfur" : "glacier"}>
                {finding.category}
              </Badge>
              {finding.auto_fixable && (
                <Badge variant="glacier">Auto-Fixable</Badge>
              )}
            </div>
            <h4 
              className="text-xs font-semibold mt-1 font-ui"
              style={{ color: TOKENS.colors.text.primary }}
            >
              {finding.title}
            </h4>
          </div>
        </div>
        <button 
          className="p-1 hover:bg-vault/50 rounded transition-colors"
          style={{ color: TOKENS.colors.text.secondary }}
        >
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {isOpen && (
        <div 
          className="px-4 pb-4 border-t text-[11px] leading-relaxed font-ui"
          style={{ 
            borderColor: TOKENS.colors.border,
            color: TOKENS.colors.text.secondary 
          }}
        >
          <div className="pt-3 font-code whitespace-pre-wrap bg-abyss p-3 border border-border rounded mt-1">
            {finding.description}
          </div>
          {finding.location_start !== undefined && finding.location_start !== null && (
            <div className="mt-2 text-[10px] flex items-center gap-1 font-code text-textMuted">
              <span>Location offset: {finding.location_start} to {finding.location_end}</span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
