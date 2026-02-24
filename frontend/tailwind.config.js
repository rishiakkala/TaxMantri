/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1a3a5c',
          50: '#f0f5fb',
          100: '#d9e8f5',
          200: '#b3d0eb',
          300: '#7baed9',
          400: '#4487c3',
          500: '#2867a8',
          600: '#1a3a5c',
          700: '#162f4a',
          800: '#112438',
          900: '#0b1926',
        },
        amber: {
          DEFAULT: '#f59e0b',
        },
        success: {
          DEFAULT: '#16a34a',
          light: '#d5f5e3',
        },
        custom: {
          dark: '#1a1924',
          purple: '#8450f5', // Vibrant purple for the animated section
          green: '#2eac85', // Vibrant green block
          grayLight: '#f6f6f9',
          textDark: '#1a1a1a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        quicksand: ['Quicksand', 'sans-serif'],
      },
      gridTemplateColumns: {
        'regime-left': '280px 1fr',
        'regime-right': '1fr 280px',
      },
    },
  },
  plugins: [],
}
