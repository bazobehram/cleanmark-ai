/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
        }
      }
    },
  },
  plugins: [],
}
