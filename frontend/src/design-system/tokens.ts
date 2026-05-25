export const TOKENS = {
  colors: {
    abyss: '#080E1A',
    pitch: '#0E1B2E',
    trench: '#152236',
    vault: '#1A2B42',
    border: '#1E3356',
    ember: '#E8860A',
    glacier: '#3CBFAE',
    sulfur: '#D4A017',
    cinder: '#C94040',
    text: {
      primary: '#E8EEF6',
      secondary: '#7A90A8',
      muted: '#3D5166'
    }
  },
  fonts: {
    ui: "IBM Plex Sans, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif",
    code: "JetBrains Mono, Cascadia Code, Fira Code, Consolas, Monaco, Courier New, monospace"
  },
  radii: {
    none: '0px',
    sm: '2px',
    md: '4px',
    lg: '6px'
  },
  transitions: {
    fast: '100ms ease-out',
    standard: '200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    enter: '280ms cubic-bezier(0.16, 1, 0.3, 1)'
  }
} as const;

export type DesignTokens = typeof TOKENS;
