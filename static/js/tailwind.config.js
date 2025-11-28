const path = require("path");
const toPosix = (p) => p.replace(/\\/g, "/");
const root = toPosix(path.resolve(__dirname, "..", ".."));

module.exports = {
  content: [
    `${root}/templates/**/*.{html,txt}`,
    `${root}/apps/**/*.py`,
    `${root}/static/src_css/**/*.css`,
    `${root}/static/css/**/*.css`,
  ],
  ignore: ["**/node_modules/**"],
  safelist: [],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0ea5a4",
          50: "#f1fcfb",
          100: "#cbf5f3",
          200: "#9aebe5",
          300: "#68e1d7",
          400: "#36d7c9",
          500: "#0ea5a4",
          600: "#0a7f82",
          700: "#07615f",
          800: "#053f3f",
          900: "#032624",
        },
        accent: "#6366f1",
        surface: "#f8fafc",
        muted: "#475569",
        border: "#e2e8f0",
        success: "#16a34a",
        warning: "#f59e0b",
        danger: "#dc2626",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "sans-serif"],
        display: ["Inter", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 12px 32px rgba(15, 23, 42, 0.12)",
      },
      borderRadius: {
        lg: "0.85rem",
        xl: "1rem",
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
    require("@tailwindcss/forms"),
    require("@tailwindcss/line-clamp"),
  ],
};
