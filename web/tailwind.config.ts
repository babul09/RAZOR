import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F4F6F8",
        ink: {
          950: "#0F172A", // ink text + dark text on gold buttons
          900: "#FFFFFF", // card surface
          800: "#F1F5F9", // subtle surface / header bg
          700: "#E7ECF3", // chip bg / hover
        },
        console: "#0B1120", // signature dark recovery readout panel
        line: "#E3E8EF",
        gold: {
          DEFAULT: "#B45309",
          dim: "#92400E",
        },
        mint: {
          DEFAULT: "#0E9F6E",
          dim: "#0B7A55",
        },
        rose: {
          DEFAULT: "#D92D20",
          dim: "#B42318",
        },
        rpay: {
          blue: "#4E7CFF",
          light: "#2F5FE0",
          navy: "#0A2540",
        },
        fg: {
          DEFAULT: "#101828",
          muted: "#5B6B7A",
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
        card: "0 1px 2px rgb(16 24 40 / 0.04), 0 12px 28px -18px rgb(16 24 40 / 0.16)",
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
