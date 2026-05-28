/** @type {import('tailwindcss').Config} */
module.exports = {
  // Escaneia todos os templates Django e arquivos JS/Alpine
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
    // Inclui classes dinâmicas geradas por Python (template tags)
    "./apps/**/templatetags/**/*.py",
  ],
  darkMode: "class", // dark mode via classe .dark no <html>

  theme: {
    extend: {
      colors: {
        // Paleta principal SafraLog — verde agrícola
        brand: {
          50:  "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a", // primary
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
          950: "#052e16",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      screens: {
        xs: "475px",
      },
      // Altura do sidebar para cálculo de layout
      spacing: {
        sidebar: "240px",
        navbar: "56px",
      },
      animation: {
        "fade-in": "fadeIn 0.15s ease-out",
        "slide-up": "slideUp 0.2s ease-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { transform: "translateY(8px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },

  plugins: [
    require("@tailwindcss/forms")({
      strategy: "class", // Não sobrescreve estilos globais
    }),
    require("@tailwindcss/typography"),
    require("@tailwindcss/aspect-ratio"),
  ],

  // Salvaguarda: garante que classes dinâmicas usadas em templatetags sejam incluídas
  safelist: [
    // Classes de status badges geradas dinamicamente em templatetags
    "bg-gray-100", "text-gray-600", "text-gray-700",
    "dark:bg-gray-800", "dark:text-gray-400",
    "bg-blue-100", "text-blue-700",
    "dark:bg-blue-900/30", "dark:text-blue-400",
    "bg-green-100", "text-green-700",
    "dark:bg-green-900/30", "dark:text-green-400",
    "bg-red-100", "text-red-700",
    "dark:bg-red-900/30", "dark:text-red-400",
    "bg-yellow-100", "text-yellow-700",
    "dark:bg-yellow-900/30", "dark:text-yellow-400",
    "bg-purple-100", "text-purple-700",
    "dark:bg-purple-900/30", "dark:text-purple-400",
  ],
};
