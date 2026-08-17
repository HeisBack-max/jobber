import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1E2761',
          dark: '#121A45',
          mid: '#243070',
          light: '#2d3d8f',
        },
        gold: {
          DEFAULT: '#C9A84C',
          light: '#E8C96A',
          pale: '#FFF8E7',
        },
        ice: '#CADCFC',
        ink: '#182033',
        slate: '#667085',
        'border-light': '#E4E8F1',
        'bg-off': '#F5F7FB',
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
