import React from "react";
import { TOKENS } from "../tokens";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input: React.FC<InputProps> = ({
  className = "",
  style,
  ...props
}) => {
  const finalStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    fontSize: "13px",
    backgroundColor: TOKENS.colors.trench,
    color: TOKENS.colors.text.primary,
    border: `1px solid ${TOKENS.colors.border}`,
    borderRadius: TOKENS.radii.sm,
    padding: "8px 12px",
    outline: "none",
    transition: `border-color ${TOKENS.transitions.fast}`,
    ...style
  };

  return (
    <input
      className={`focus:border-ember focus:ring-1 focus:ring-ember ${className}`}
      style={finalStyles}
      {...props}
    />
  );
};
