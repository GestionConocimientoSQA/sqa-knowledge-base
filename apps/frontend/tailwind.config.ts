import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx,js,jsx,mdx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--color-border))",
        input: "hsl(var(--color-input))",
        ring: "hsl(var(--color-ring))",
        background: "hsl(var(--color-background))",
        foreground: "hsl(var(--color-foreground))",
        primary: {
          DEFAULT: "hsl(var(--color-brand-primary))",
          foreground: "hsl(var(--color-brand-primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--color-muted))",
          foreground: "hsl(var(--color-muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--color-error))",
          foreground: "hsl(0 0% 100%)",
        },
        muted: {
          DEFAULT: "hsl(var(--color-muted))",
          foreground: "hsl(var(--color-muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--color-brand-accent))",
          foreground: "hsl(0 0% 100%)",
        },
        popover: {
          DEFAULT: "hsl(var(--color-background))",
          foreground: "hsl(var(--color-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--color-card))",
          foreground: "hsl(var(--color-foreground))",
        },
        success: "hsl(var(--color-success))",
        warning: "hsl(var(--color-warning))",
        info: "hsl(var(--color-info))",
        // SQA brand
        sqa: {
          "azul-claro": "hsl(204 67% 62%)",
          "azul-medio-claro": "hsl(202 100% 43%)",
          "azul-medio": "hsl(211 100% 36%)",
          "azul-oscuro": "hsl(212 100% 14%)",
          "azul-corp": "hsl(222 96% 25%)",
          "azul-bright": "hsl(225 100% 33%)",
          ink: "hsl(231 65% 9%)",
          naranja: "hsl(36 97% 53%)",
          "naranja-soft": "hsl(41 100% 63%)",
          amarillo: "hsl(40 96% 64%)",
        },
        // Domain
        authoritative: "hsl(var(--color-authoritative))",
        "score-high": "hsl(var(--color-score-high))",
        "score-medium": "hsl(var(--color-score-medium))",
        "score-low": "hsl(var(--color-score-low))",
        // Folder categories
        "cat-PROC": "hsl(var(--color-cat-PROC))",
        "cat-TEC": "hsl(var(--color-cat-TEC))",
        "cat-ARQ": "hsl(var(--color-cat-ARQ))",
        "cat-HERR": "hsl(var(--color-cat-HERR))",
        "cat-NEG": "hsl(var(--color-cat-NEG))",
        "cat-ENV": "hsl(var(--color-cat-ENV))",
        "cat-EST": "hsl(var(--color-cat-EST))",
        "cat-CONT": "hsl(var(--color-cat-CONT))",
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius)",
        sm: "var(--radius-sm)",
      },
      fontFamily: {
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-halo": {
          "0%": { boxShadow: "0 0 0 0 hsl(36 97% 53% / 0.5)" },
          "100%": { boxShadow: "0 0 0 16px hsl(36 97% 53% / 0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 220ms cubic-bezier(0.22, 1, 0.36, 1)",
        "accordion-up": "accordion-up 220ms cubic-bezier(0.22, 1, 0.36, 1)",
        "fade-up": "fade-up 280ms cubic-bezier(0.22, 1, 0.36, 1) both",
        "pulse-halo": "pulse-halo 1.6s ease-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
