import React from "react";
import { TOKENS } from "../tokens";

export const SkeletonCard: React.FC = () => {
  const cardStyle: React.CSSProperties = {
    backgroundColor: TOKENS.colors.pitch,
    border: `1px solid ${TOKENS.colors.border}`,
    borderRadius: TOKENS.radii.sm,
    padding: "16px",
    position: "relative",
    overflow: "hidden",
    height: "120px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between"
  };

  return (
    <div style={cardStyle}>
      {/* Shimmer loading mask */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
      
      <div className="space-y-3">
        {/* Title skeleton */}
        <div 
          className="h-4 w-2/3 rounded" 
          style={{ backgroundColor: TOKENS.colors.trench }} 
        />
        {/* Subtitle skeleton */}
        <div 
          className="h-3 w-5/6 rounded" 
          style={{ backgroundColor: TOKENS.colors.trench }} 
        />
        <div 
          className="h-3 w-1/2 rounded" 
          style={{ backgroundColor: TOKENS.colors.trench }} 
        />
      </div>
      
      {/* Footnote skeleton */}
      <div className="flex justify-between items-center mt-4">
        <div 
          className="h-3 w-1/4 rounded" 
          style={{ backgroundColor: TOKENS.colors.trench }} 
        />
        <div 
          className="h-4 w-10 rounded-sm" 
          style={{ backgroundColor: TOKENS.colors.trench }} 
        />
      </div>
    </div>
  );
};
