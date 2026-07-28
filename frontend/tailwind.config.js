/** @type {import('tailwindcss').Config} */

/*
 * AcaFund design tokens — "raw ledger".
 *
 * Source palette:
 *   Taupe Grey  #54494B — warm ink. Everything reads against this, not black.
 *   Mint Cream  #F1F7ED — paper
 *   Muted Teal  #91C7B1 — credit / verified
 *   Rosewood    #B33951 — debit, CTA, the loud one
 *   Light Gold  #E3D081 — highlight / marker
 *
 * Colour is used as flat saturated blocks, never as tints or gradients.
 * The semantic token names are unchanged so the ~36 app screens restyle
 * from here rather than needing 230 edits.
 */

// Warm ink, from Taupe Grey.
const ink = {
  900: '#241E1F',
  800: '#332B2C',
  700: '#443A3C',
  600: '#54494B', // canonical Taupe Grey
  500: '#6E6264',
  400: '#8C8082',
  300: '#B0A6A8',
  200: '#D2CBCC',
  100: '#E8E4E4',
  50:  '#F3F1F1',
}

// Paper, from Mint Cream.
const paper = {
  0:   '#FFFFFF',
  50:  '#F8FBF6',
  100: '#F1F7ED', // canonical Mint Cream
  200: '#E4EDDE',
  300: '#D3E0CB',
  400: '#BFD1B4',
}

// Rosewood.
const rose = {
  900: '#3E1219',
  800: '#5E1C27',
  700: '#8A2B3E',
  600: '#B33951', // canonical Rosewood
  500: '#C55068',
  400: '#D67C8E',
  300: '#E5A9B5',
  200: '#F1D0D7',
  100: '#F9E8EC',
}

// Muted Teal.
const teal = {
  900: '#1F3B31',
  800: '#2C5546',
  700: '#3F7A64',
  600: '#57967C',
  500: '#74B097',
  400: '#91C7B1', // canonical Muted Teal
  300: '#AFD8C4',
  200: '#CDE7D9',
  100: '#E7F3EE',
}

// Light Gold.
const gold = {
  900: '#4A3F12',
  800: '#6B5B1D',
  700: '#8C7828',
  600: '#AD9639',
  500: '#C9B356',
  400: '#E3D081', // canonical Light Gold
  300: '#EADDA3',
  200: '#F2E9C6',
  100: '#F9F5E4',
}

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Remapped so legacy `border-black` / `bg-black` land on warm ink.
        black: ink[900],
        ink,
        paper,
        rose,
        teal,
        gold,

        // --- semantic tokens (names preserved) ---
        background: paper[100],
        surface: paper[100],
        'surface-bright': paper[0],
        'surface-dim': paper[300],
        'surface-variant': paper[200],
        'surface-tint': rose[600],
        'surface-container-lowest': paper[0],
        'surface-container-low': paper[50],
        'surface-container': paper[200],
        'surface-container-high': paper[300],
        'surface-container-highest': paper[400],

        'on-background': ink[900],
        'on-surface': ink[900],
        'on-surface-variant': ink[500],
        outline: ink[400],
        'outline-variant': ink[200],
        'inverse-surface': ink[900],
        'inverse-on-surface': paper[100],
        'inverse-primary': rose[300],

        primary: rose[600],
        'on-primary': '#FFFFFF',
        'primary-container': rose[100],
        'on-primary-container': rose[900],
        'primary-fixed': rose[100],
        'primary-fixed-dim': rose[200],
        'on-primary-fixed': rose[900],
        'on-primary-fixed-variant': rose[700],

        secondary: teal[700],
        'on-secondary': '#FFFFFF',
        'secondary-container': teal[400],
        'on-secondary-container': teal[900],
        'secondary-fixed': teal[100],
        'secondary-fixed-dim': teal[300],
        'on-secondary-fixed': teal[900],
        'on-secondary-fixed-variant': teal[800],

        tertiary: gold[700],
        'on-tertiary': ink[900],
        'tertiary-container': gold[400],
        'on-tertiary-container': gold[900],
        'tertiary-fixed': gold[100],
        'tertiary-fixed-dim': gold[300],
        'on-tertiary-fixed': gold[900],
        'on-tertiary-fixed-variant': gold[800],

        success: teal,
        error: rose[700],
        'on-error': '#FFFFFF',
        'error-container': rose[100],
        'on-error-container': rose[900],
        danger: rose,
      },

      // Raw: hairlines are 1px, structural rules are 2px.
      borderWidth: { 2: '1px', 3: '2px', 4: '2px', 6: '3px' },

      // Raw means square. Only pills stay round.
      borderRadius: {
        none: '0',
        DEFAULT: '0',
        sm: '0',
        lg: '0',
        xl: '0',
        '2xl': '0',
        '3xl': '0',
        full: '9999px',
      },

      spacing: {
        unit: '4px',
        'stroke-thick': '2px',
        'margin-desktop': '48px',
        gutter: '24px',
        'stroke-thin': '1px',
        'margin-mobile': '16px',
      },

      fontFamily: {
        // Display carries the poster weight; body is the same superfamily so
        // the page stays coherent; mono is reserved for ledger data, where
        // monospacing is what the content actually is.
        display: ['"Archivo Black"', 'Archivo', 'system-ui', 'sans-serif'],
        sans: ['Archivo', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Space Mono"', 'ui-monospace', 'monospace'],
      },

      fontSize: {
        'display-xl': ['clamp(3.25rem,9vw,8.5rem)', { lineHeight: '0.88', letterSpacing: '-0.045em' }],
        'display-lg': ['clamp(2.75rem,7vw,6rem)', { lineHeight: '0.92', letterSpacing: '-0.04em' }],
        'display-md': ['clamp(2rem,4.5vw,3.5rem)', { lineHeight: '0.98', letterSpacing: '-0.035em' }],
        'headline-lg': ['clamp(1.9rem,3.6vw,3.25rem)', { lineHeight: '1.0', letterSpacing: '-0.035em' }],
        'headline-lg-mobile': ['1.9rem', { lineHeight: '1.02', letterSpacing: '-0.03em' }],
        'headline-md': ['1.35rem', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
        'body-lg': ['1.0625rem', { lineHeight: '1.6', fontWeight: '400' }],
        'body-md': ['0.9375rem', { lineHeight: '1.6', fontWeight: '400' }],
        'label-bold': ['0.6875rem', { lineHeight: '1', letterSpacing: '0.16em', fontWeight: '700' }],
      },

      boxShadow: {
        // Solid offset print shadows — no blur anywhere.
        'neo-sm': `2px 2px 0 0 ${ink[900]}`,
        neo: `4px 4px 0 0 ${ink[900]}`,
        'neo-lg': `7px 7px 0 0 ${ink[900]}`,
        lift: `7px 7px 0 0 ${ink[900]}`,
        rose: `4px 4px 0 0 ${rose[600]}`,
        teal: `4px 4px 0 0 ${teal[700]}`,
        gold: `4px 4px 0 0 ${gold[600]}`,
        glow: `4px 4px 0 0 ${ink[900]}`,
      },

      backgroundImage: {
        grain:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E\")",
      },

      transitionTimingFunction: {
        soft: 'cubic-bezier(0.22, 1, 0.36, 1)',
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        step: 'cubic-bezier(0.85, 0, 0.15, 1)',
      },

      keyframes: {
        'fade-up': { from: { opacity: '0', transform: 'translateY(14px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        marquee: { from: { transform: 'translateX(0)' }, to: { transform: 'translateX(-50%)' } },
        'marquee-rev': { from: { transform: 'translateX(-50%)' }, to: { transform: 'translateX(0)' } },
        // A ledger row lands: slides in from the left edge and settles.
        'print-row': {
          '0%': { opacity: '0', transform: 'translateX(-14px)' },
          '60%': { opacity: '1' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'rise-line': {
          from: { transform: 'translateY(105%)' },
          to: { transform: 'translateY(0)' },
        },
        blink: { '0%,49%': { opacity: '1' }, '50%,100%': { opacity: '0' } },
        'pulse-dot': {
          '0%,100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.35', transform: 'scale(0.82)' },
        },
        'bar-grow': { from: { transform: 'scaleX(0)' }, to: { transform: 'scaleX(1)' } },
        'stamp-in': {
          '0%': { opacity: '0', transform: 'scale(1.6) rotate(-14deg)' },
          '70%': { opacity: '1', transform: 'scale(0.94) rotate(-6deg)' },
          '100%': { opacity: '1', transform: 'scale(1) rotate(-6deg)' },
        },
      },

      animation: {
        'fade-up': 'fade-up 0.6s cubic-bezier(0.22,1,0.36,1) both',
        'fade-in': 'fade-in 0.5s ease both',
        marquee: 'marquee 34s linear infinite',
        'marquee-rev': 'marquee-rev 42s linear infinite',
        'print-row': 'print-row 0.45s cubic-bezier(0.22,1,0.36,1) both',
        'rise-line': 'rise-line 0.85s cubic-bezier(0.22,1,0.36,1) both',
        blink: 'blink 1.1s steps(1) infinite',
        'pulse-dot': 'pulse-dot 1.6s ease-in-out infinite',
        'bar-grow': 'bar-grow 1.1s cubic-bezier(0.22,1,0.36,1) both',
        'stamp-in': 'stamp-in 0.5s cubic-bezier(0.34,1.56,0.64,1) both',
      },
    },
  },
  plugins: [],
}
