/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
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
        textPrimary: '#E8EEF6',
        textSecondary: '#7A90A8',
        textMuted: '#3D5166',
      },
      fontFamily: {
        ui: ["IBM Plex Sans", "system-ui", "sans-serif"],
        code: ["JetBrains Mono", "monospace"],
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        }
      },
      animation: {
        shimmer: 'shimmer 1.5s infinite',
      }
    },
  },
  plugins: [],
}
