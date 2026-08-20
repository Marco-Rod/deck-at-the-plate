/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        koshien: {
          dark: "#121619",       // Negro pizarra vintage
          green: "#1A3323",      // Verde hiedra Koshien / Wrigley
          lightGreen: "#2D5A3F", // Verde césped clásico
          cream: "#E6DFD3",      // Tono marfil
          chalk: "#F7F5F0",      // Blanco tiza
          gold: "#C5A059",       // Dorado latón de trofeos
          border: "#2C3E35"      // Borde verde oscuro
        }
      },
      fontFamily: {
        sports: ["Teko", "serif"],
        vintage: ["'Courier Prime'", "monospace"],
        body: ["Inter", "sans-serif"],
      },
      boxShadow: {
        'scoreboard': '0 4px 20px -2px rgba(0, 0, 0, 0.8), inset 0 1px 2px rgba(255, 255, 255, 0.1)',
        'vintage-card': '0 10px 25px -5px rgba(0, 0, 0, 0.9), 0 0 0 2px #C5A059',
      }
    },
  },
  plugins: [],
}