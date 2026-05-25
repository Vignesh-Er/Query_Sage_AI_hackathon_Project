import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { TrendingUp, AlertOctagon } from "lucide-react";

interface RegressionBannerProps {
  previousCost: number;
  currentCost: number;
  deltaPercent: number;
}

export const RegressionBanner: React.FC<RegressionBannerProps> = ({
  previousCost,
  currentCost,
  deltaPercent
}) => {
  return (
    <div 
      className="p-4 border mb-4 flex items-center justify-between animate-pulse"
      style={{
        backgroundColor: `${TOKENS.colors.cinder}0D`,
        borderColor: TOKENS.colors.cinder,
        borderLeftWidth: "4px"
      }}
    >
      <div className="flex items-center gap-3">
        <div 
          className="p-2 rounded-sm"
          style={{ backgroundColor: `${TOKENS.colors.cinder}1A`, color: TOKENS.colors.cinder }}
        >
          <AlertOctagon size={20} />
        </div>
        <div>
          <h4 
            className="text-xs font-bold uppercase tracking-wider font-ui"
            style={{ color: TOKENS.colors.cinder }}
          >
            Cost Regression Detected
          </h4>
          <p 
            className="text-[11px] mt-0.5 font-ui"
            style={{ color: TOKENS.colors.text.secondary }}
          >
            Execution cost has surged by {deltaPercent.toFixed(1)}% compared to the previous query run of this fingerprint.
          </p>
        </div>
      </div>
      <div className="text-right flex items-center gap-4 font-code text-xs">
        <div>
          <span className="block text-[10px] uppercase font-ui tracking-wider text-textMuted">PREVIOUS COST</span>
          <span style={{ color: TOKENS.colors.text.primary }}>{previousCost.toFixed(2)}</span>
        </div>
        <div style={{ color: TOKENS.colors.cinder }}>
          <TrendingUp size={16} className="inline mr-1" />
          <span className="block text-[10px] uppercase font-ui tracking-wider text-textMuted">CURRENT COST</span>
          <span className="font-bold">{currentCost.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};
