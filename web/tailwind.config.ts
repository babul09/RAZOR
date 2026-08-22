import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070B14",
          900: "#0C1220",
          800: "#131C30",
          700: "#1A2540",
        },
        line: "#1E2A47",
        gold: {
          DEFAULT: "#E8B84B",
          dim: "#B98A2A",
        },
        mint: {
          DEFAULT: "#3DDC97",
          dim: "#2AA678",
        },
        rose: {
          DEFAULT: "#F4707B",
          dim: "#C24A57",
        },
        rpay: {
          blue: "#4E7CFF",
          light: "#6E9BFF",
          navy: "#0A2540",
        },
        fg: {
          DEFAULT: "#E8EDF6",
          muted: "#8B96AE",
        },
      },
      fontFamily: {
        sans: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "ui-sans-serif", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "0.625rem",
      },
      boxShadow: {
        card: "0 1px 0 0 rgb(232 184 75 / 0.06), 0 8px 24px -12px rgb(0 0 0 / 0.6)",
      },
      fontSize: {
        hero: ["3.5rem", { lineHeight: "1", fontWeight: "600" }],
        eyebrow: ["0.72rem", { lineHeight: "1.2", letterSpacing: "0.18em" }],
      },
      animation: {
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
