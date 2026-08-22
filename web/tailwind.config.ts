import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4f46e5",
          dark: "#3730a3",
          light: "#eef2ff",
        },
        success: {
          DEFAULT: "#059669",
          light: "#ecfdf5",
        },
        warning: {
          DEFAULT: "#d97706",
          light: "#fffbeb",
        },
        danger: {
          DEFAULT: "#e11d48",
          light: "#fff1f2",
        },
        surface: "#ffffff",
        ink: {
          DEFAULT: "#0f172a",
          muted: "#64748b",
        },
      },
      borderRadius: {
        card: "0.75rem",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.08)",
      },
      fontSize: {
        headline: ["2.25rem", { lineHeight: "1.15", fontWeight: "700" }],
        card: ["0.875rem", { lineHeight: "1.4" }],
      },
    },
  },
  plugins: [],
};

export default config;
