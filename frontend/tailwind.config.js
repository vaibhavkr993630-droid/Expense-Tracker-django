/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#4361ee",
        "primary-dark": "#3451d1",
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
        bg: "#0d0d1a",
        card: "#1a1a2e",
        border: "#2a2a45",
        muted: "#6b7280",
      },
    },
  },
  plugins: [],
}

