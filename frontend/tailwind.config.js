/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0f766e", soft: "#ccfbf1" },
        cup: {
          grass: "#0b6b43",
          deep: "#064e3b",
          gold: "#f6c453",
          line: "#dff7ea",
          red: "#e11d48",
        },
      },
    },
  },
  plugins: [],
};
