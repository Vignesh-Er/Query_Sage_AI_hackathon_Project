import React, { useState } from "react";
import { TOKENS } from "../tokens";

interface TooltipProps {
  content: string;
  children: React.ReactElement;
  position?: "top" | "bottom" | "left" | "right";
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = "top"
}) => {
  const [visible, setVisible] = useState(false);

  const getPositionClasses = (): string => {
    switch (position) {
      case "bottom":
        return "top-full left-1/2 -translate-x-1/2 mt-2";
      case "left":
        return "right-full top-1/2 -translate-y-1/2 mr-2";
      case "right":
        return "left-full top-1/2 -translate-y-1/2 ml-2";
      case "top":
      default:
        return "bottom-full left-1/2 -translate-x-1/2 mb-2";
    }
  };

  const tooltipStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    fontSize: "11px",
    backgroundColor: TOKENS.colors.vault,
    color: TOKENS.colors.text.primary,
    border: `1px solid ${TOKENS.colors.border}`,
    borderRadius: TOKENS.radii.sm,
    padding: "6px 10px",
    boxShadow: "0 4px 10px rgba(0,0,0,0.3)",
    whiteSpace: "nowrap",
    zIndex: 1000,
    pointerEvents: "none"
  };

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div
          className={`absolute ${getPositionClasses()} transition-opacity duration-200`}
          style={tooltipStyles}
        >
          {content}
        </div>
      )}
    </div>
  );
};
