/** @type {import('tailwindcss').Config} */
const config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    // We overwrite standard colors to enforce the strict palette
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: '#FFFFFF',
      primary: '#111111',
      background: '#FDFCFB',
      surface: '#F4F4F0',
      text: '#222222',
      muted: '#888883',
      border: '#E5E5E0',
      // Explicit success state from the design doc
      success: '#10B981', 
    },
    extend: {
      fontFamily: {
        sans: ['Satoshi', 'sans-serif'],
        serif: ['Newsreader', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-sunset': 'linear-gradient(135deg, #3B82F6 0%, #8B5CF6 35%, #F97316 70%, #FCD34D 100%)',
      },
      borderRadius: {
        // Enforcing the strict 4px geometric radius globally
        DEFAULT: '4px',
        md: '4px',
        lg: '4px',
      },
      boxShadow: {
        // Explicitly removing standard shadows to force depth via color shifts
        sm: 'none',
        DEFAULT: 'none',
        md: 'none',
        lg: 'none',
        xl: 'none',
        '2xl': 'none',
        inner: 'none',
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      }
    },
  },
  plugins: [],
};

export default config;
