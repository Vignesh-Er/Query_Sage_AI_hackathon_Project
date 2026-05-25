import { TOKENS } from "./tokens";

export const MONACO_THEME_NAME = "querysage-dark-theme";

export const MONACO_THEME = {
  base: "vs-dark" as const,
  inherit: true,
  rules: [
    { token: "keyword", foreground: TOKENS.colors.ember.replace("#", "") },
    { token: "string", foreground: TOKENS.colors.glacier.replace("#", "") },
    { token: "number", foreground: TOKENS.colors.sulfur.replace("#", "") },
    { token: "comment", foreground: TOKENS.colors.text.muted.replace("#", ""), fontStyle: "italic" },
    { token: "predefined", foreground: "E88080" }, // functions
    { token: "operator", foreground: TOKENS.colors.text.secondary.replace("#", "") },
    { token: "type", foreground: TOKENS.colors.text.primary.replace("#", "") },
    { token: "identifier", foreground: TOKENS.colors.text.primary.replace("#", "") }
  ],
  colors: {
    "editor.background": TOKENS.colors.trench,
    "editor.foreground": TOKENS.colors.text.primary,
    "editorCursor.foreground": TOKENS.colors.ember,
    "editor.lineHighlightBackground": "#1C2E48",
    "editorLineNumber.foreground": "#2A4060",
    "editorLineNumber.activeForeground": TOKENS.colors.ember,
    "editor.selectionBackground": "#1E3356"
  }
};
