/** @type {import('tailwindcss').Config} */
export default {
  content: ['./app/**/*.{js,jsx}', './components/**/*.{js,jsx}', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', '"SF Mono"', '"Fira Code"', 'monospace'],
      },
    },
  },
  plugins: [],
};
