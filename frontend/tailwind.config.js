/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          green: '#8abf9e', 
          yellow: '#f2ac2a', 
          orange: '#f6eee7',
          darker: '#53443b'  //'#605541'
        }
      }
    },
  },
  plugins: [],
}
