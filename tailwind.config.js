/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'neon-cyan': '#08F7FE',
      },
      boxShadow: {
        'glow': '0 0 15px rgba(8, 247, 254, 0.5), 0 0 5px rgba(8, 247, 254, 0.6)',
      }
    },
  },
  plugins: [],
}
