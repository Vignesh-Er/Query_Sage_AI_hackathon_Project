import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import { Info, HelpCircle } from "lucide-react";

interface AssumptionItem {
  context: string;
  assumption: string;
}

interface AssumptionsPanelProps {
  assumptions?: AssumptionItem[];
}

export const AssumptionsPanel: React.FC<AssumptionsPanelProps> = ({ assumptions }) => {
  if (!assumptions || assumptions.length === 0) return null;

  return (
    <div className="mt-4" style={{ fontFamily: TOKENS.fonts.ui }}>
      <h3 
        className="text-[10px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5"
        style={{ color: TOKENS.colors.text.secondary }}
      >
        <HelpCircle size={14} className="text-ember" />
        <span>Logical Parsing Assumptions</span>
      </h3>
      <div className="space-y-2">
        {assumptions.map((item, idx) => (
          <Card key={idx} className="p-3 bg-vault/10 border-border/80">
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-ember uppercase tracking-wider mb-1">
              <Info size={12} />
              <span>Scope: {item.context}</span>
            </div>
            <p className="text-[11px] text-textSecondary leading-relaxed">
              {item.assumption}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
};
