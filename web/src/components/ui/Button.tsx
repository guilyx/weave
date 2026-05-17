import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const styles: Record<Variant, string> = {
  primary:
    "bg-gold text-ink hover:bg-gold-bright shadow-lg shadow-gold/20",
  secondary:
    "border border-border bg-surface-raised text-parchment hover:border-gold/50",
  ghost: "text-muted hover:text-parchment hover:bg-white/5",
  danger: "bg-crimson/80 text-parchment hover:bg-crimson",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-base font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
