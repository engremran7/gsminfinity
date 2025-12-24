/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './apps/**/templates/**/*.html',
    './templates/**/*.html',
    './static/**/*.js',
    './static/**/*.ts',
  ],

  // JIT mode enabled by default in Tailwind 3.x
  mode: 'jit',

  darkMode: 'class',
  
  theme: {
    extend: {
      colors: {
        // Enterprise Admin Theme
        admin: {
          bg: '#050915',
          panel: '#0f172a',
          'panel-light': 'rgba(15, 23, 42, 0.72)',
          'panel-strong': 'rgba(15, 23, 42, 0.92)',
          card: 'rgba(255, 255, 255, 0.04)',
          glass: 'rgba(255, 255, 255, 0.08)',
          line: 'rgba(255, 255, 255, 0.08)',
          text: '#e2e8f0',
          muted: '#9ca3af',
        },
        primary: {
          DEFAULT: '#6b8bff',
          dark: '#4f46e5',
          light: '#818cf8',
        },
        accent: {
          DEFAULT: '#2dd4bf',
          pink: '#f472b6',
          amber: '#fbbf24',
        },
        security: {
          high: '#ef4444',
          medium: '#f59e0b',
          low: '#22c55e',
        },
      },
      
      fontFamily: {
        sans: ['Inter', 'Space Grotesk', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      
      fontSize: {
        'xs': ['0.6875rem', { lineHeight: '1rem' }],
        'sm': ['0.8125rem', { lineHeight: '1.25rem' }],
        'base': ['0.9375rem', { lineHeight: '1.5rem' }],
        'lg': ['1.0625rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.875rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      
      borderRadius: {
        'xs': '0.25rem',
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.75rem',
        'xl': '1rem',
        '2xl': '1.125rem',
        '3xl': '1.5rem',
      },
      
      boxShadow: {
        'xs': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'sm': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'DEFAULT': '0 4px 16px rgba(0, 0, 0, 0.12)',
        'md': '0 8px 24px rgba(0, 0, 0, 0.18)',
        'lg': '0 12px 36px rgba(0, 0, 0, 0.25)',
        'xl': '0 18px 60px rgba(0, 0, 0, 0.35)',
        '2xl': '0 25px 80px rgba(0, 0, 0, 0.45)',
        'glow': '0 0 24px rgba(107, 139, 255, 0.35)',
        'glow-accent': '0 0 24px rgba(45, 212, 191, 0.35)',
        'inner': 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',
      },
      
      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        'DEFAULT': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '24px',
      },
      
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'fade-in-up': 'fadeInUp 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-in-down': 'slideInDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        'bounce-subtle': 'bounceSubtle 1s ease-in-out infinite',
      },
      
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideInDown: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 20px rgba(107, 139, 255, 0.3)' },
          '50%': { opacity: '0.8', boxShadow: '0 0 40px rgba(107, 139, 255, 0.6)' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      
      transitionDuration: {
        '0': '0ms',
        '75': '75ms',
        '100': '100ms',
        '150': '150ms',
        '180': '180ms',
        '200': '200ms',
        '250': '250ms',
        '300': '300ms',
        '350': '350ms',
        '400': '400ms',
        '500': '500ms',
      },
      
      spacing: {
        '18': '4.5rem',
        '112': '28rem',
        '128': '32rem',
      },
      
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },
  
  plugins: [
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
    require('@tailwindcss/typography'),
    require('@tailwindcss/line-clamp'),
    
    // Custom plugin for admin-specific utilities
    function({ addUtilities, addComponents, theme }) {
      const newUtilities = {
        '.glassmorphism': {
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(14px)',
          borderColor: 'rgba(255, 255, 255, 0.08)',
        },
        '.glassmorphism-strong': {
          background: 'rgba(255, 255, 255, 0.12)',
          backdropFilter: 'blur(20px)',
          borderColor: 'rgba(255, 255, 255, 0.12)',
        },
        '.text-balance': {
          textWrap: 'balance',
        },
        '.text-pretty': {
          textWrap: 'pretty',
        },
        '.scrollbar-thin': {
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255, 255, 255, 0.2) transparent',
        },
        '.no-scrollbar': {
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
      }
      
      const newComponents = {
        '.admin-gradient': {
          background: 'linear-gradient(120deg, #6b8bff, #2dd4bf)',
        },
        '.admin-gradient-vertical': {
          background: 'linear-gradient(180deg, #6b8bff, #2dd4bf)',
        },
        '.admin-gradient-radial': {
          background: 'radial-gradient(circle at center, #6b8bff, #2dd4bf)',
        },
        '.security-gradient-high': {
          background: 'linear-gradient(120deg, #ef4444, #dc2626)',
        },
        '.security-gradient-medium': {
          background: 'linear-gradient(120deg, #f59e0b, #d97706)',
        },
        '.security-gradient-low': {
          background: 'linear-gradient(120deg, #22c55e, #16a34a)',
        },
      }
      
      addUtilities(newUtilities)
      addComponents(newComponents)
    },
  ],
}
