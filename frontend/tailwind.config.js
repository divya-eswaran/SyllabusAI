/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        primary: {
          50: '#f0f4ff',
          100: '#e0e9ff',
          200: '#c7d7ff',
          300: '#a5bbff',
          400: '#8098ff',
          500: '#6172f5',
          600: '#4e55e8',
          700: '#4044d0',
          800: '#3437a8',
          900: '#2f3285',
          950: '#1c1d4f',
        },
        accent: {
          50: '#fff1f0',
          100: '#ffe4e1',
          200: '#ffcdc7',
          300: '#ffaa9e',
          400: '#ff7b6a',
          500: '#ff5240',
          600: '#ed3120',
          700: '#c82415',
          800: '#a52215',
          900: '#882319',
        },
        surface: {
          900: '#0d0e1a',
          800: '#12142b',
          700: '#191c38',
          600: '#222645',
          500: '#2d3158',
          400: '#3d4270',
        },
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #0d0e1a 0%, #12142b 40%, #1c1d4f 100%)',
        'card-gradient': 'linear-gradient(145deg, rgba(97,114,245,0.08) 0%, rgba(255,82,64,0.04) 100%)',
        'shimmer': 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(97, 114, 245, 0.4)' },
          '50%': { boxShadow: '0 0 0 12px rgba(97, 114, 245, 0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      boxShadow: {
        'glow': '0 0 24px rgba(97, 114, 245, 0.25)',
        'glow-accent': '0 0 24px rgba(255, 82, 64, 0.25)',
        'card': '0 4px 24px rgba(0,0,0,0.4)',
        'card-hover': '0 8px 40px rgba(0,0,0,0.6)',
      },
    },
  },
  plugins: [],
}
