import React from "react";
import { TOKENS } from "../tokens";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  isLoading = false,
  className = "",
  style,
  ...props
}) => {
  const baseStyle: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    fontSize: "11px",
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    fontWeight: 600,
    borderRadius: TOKENS.radii.none,
    transition: `all ${TOKENS.transitions.fast}`,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "8px 16px",
    cursor: "pointer",
    border: "none",
    outline: "none",
    position: "relative",
    overflow: "hidden"
  };

  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case "secondary":
        return {
          backgroundColor: TOKENS.colors.trench,
          color: TOKENS.colors.text.primary,
          border: `1px solid ${TOKENS.colors.border}`
        };
      case "danger":
        return {
          backgroundColor: TOKENS.colors.cinder,
          color: TOKENS.colors.text.primary
        };
      case "ghost":
        return {
          backgroundColor: "transparent",
          color: TOKENS.colors.text.secondary,
          border: "none"
        };
      case "primary":
      default:
        return {
          backgroundColor: TOKENS.colors.ember,
          color: TOKENS.colors.text.primary
        };
    }
  };

  const finalStyles = { ...baseStyle, ...getVariantStyles(), ...style };

  return (
    <button
      className={`relative active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed group ${className}`}
      style={finalStyles}
      disabled={isLoading}
      {...props}
    >
      {/* Shimmer loading scanning gradient */}
      {isLoading && (
        <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-[shimmer_1.2s_infinite]" />
      )}
      
      <span className={isLoading ? "opacity-30" : ""}>{children}</span>
    </button>
  );
};
