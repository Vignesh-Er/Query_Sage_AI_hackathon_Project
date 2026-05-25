import React from "react";
import { TOKENS } from "../tokens";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  severity?: number;
  bg?: "pitch" | "trench" | "vault";
}

export const Card: React.FC<CardProps> = ({
  children,
  severity = 0,
  bg = "pitch",
  className = "",
  style,
  ...props
}) => {
  const getBorderColor = (): string => {
    if (severity >= 7) return TOKENS.colors.cinder;
    if (severity >= 4) return TOKENS.colors.sulfur;
    if (severity >= 1) return TOKENS.colors.text.secondary;
    return TOKENS.colors.border;
  };

  const getBgColor = (): string => {
    switch (bg) {
      case "trench":
        return TOKENS.colors.trench;
      case "vault":
        return TOKENS.colors.vault;
      case "pitch":
      default:
        return TOKENS.colors.pitch;
    }
  };

  const finalStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    backgroundColor: getBgColor(),
    borderLeft: severity > 0 ? `4px solid ${getBorderColor()}` : "none",
    borderTop: severity === 0 ? `1px solid ${TOKENS.colors.border}` : "none",
    borderRight: severity === 0 ? `1px solid ${TOKENS.colors.border}` : "none",
    borderBottom: severity === 0 ? `1px solid ${TOKENS.colors.border}` : "none",
    borderRadius: TOKENS.radii.sm,
    padding: "16px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    ...style
  };

  return (
    <div className={className} style={finalStyles} {...props}>
      {children}
    </div>
  );
};
