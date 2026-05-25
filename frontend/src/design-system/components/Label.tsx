import React from "react";
import { TOKENS } from "../tokens";

interface LabelProps extends React.HTMLAttributes<HTMLSpanElement> {
  color?: "primary" | "secondary" | "muted" | "ember" | "glacier" | "cinder";
}

export const Label: React.FC<LabelProps> = ({
  children,
  color = "secondary",
  className = "",
  style,
  ...props
}) => {
  const getTextColor = (): string => {
    switch (color) {
      case "primary":
        return TOKENS.colors.text.primary;
      case "muted":
        return TOKENS.colors.text.muted;
      case "ember":
        return TOKENS.colors.ember;
      case "glacier":
        return TOKENS.colors.glacier;
      case "cinder":
        return TOKENS.colors.cinder;
      case "secondary":
      default:
        return TOKENS.colors.text.secondary;
    }
  };

  const finalStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontWeight: 600,
    color: getTextColor(),
    ...style
  };

  return (
    <span className={className} style={finalStyles} {...props}>
      {children}
    </span>
  );
};
