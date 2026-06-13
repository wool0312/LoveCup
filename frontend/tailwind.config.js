/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#e11d48", soft: "#fecdd3" },
      },
    },
  },
  plugins: [],
};
