
// PostCSS config normalized for reproducible builds.

module.exports = {
  plugins: {
    tailwindcss: {
      // Enforce deterministic class ordering across environments
      config: "./tailwind.config.js",
    },
    autoprefixer: {
      flexbox: "no-2009",
    },
  },
};

