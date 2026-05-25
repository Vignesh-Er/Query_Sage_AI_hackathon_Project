import React from "react";
import { TOKENS } from "../tokens";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "performance" | "correctness" | "style" | "index" | "locking" | "neutral" | "cinder" | "sulfur" | "glacier";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  className = "",
  style,
  ...props
}) => {
  const getColors = (): { bg: string; text: string } => {
    switch (variant) {
      case "performance":
      case "locking":
      case "cinder":
        return { bg: `${TOKENS.colors.cinder}14`, text: TOKENS.colors.cinder };
      case "correctness":
      case "sulfur":
        return { bg: `${TOKENS.colors.sulfur}14`, text: TOKENS.colors.sulfur };
      case "index":
      case "glacier":
        return { bg: `${TOKENS.colors.glacier}14`, text: TOKENS.colors.glacier };
      case "style":
      default:
        return { bg: `${TOKENS.colors.text.secondary}14`, text: TOKENS.colors.text.secondary };
    }
  };

  const { bg, text } = getColors();

  const finalStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.code,
    fontSize: "10px",
    fontWeight: 600,
    backgroundColor: bg,
    color: text,
    padding: "3px 8px",
    borderRadius: TOKENS.radii.sm,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    ...style
  };

  return (
    <span className={className} style={finalStyles} {...props}>
      {children}
    </span>
  );
};
