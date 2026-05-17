import type { LucideIcon } from "lucide-react";

const tones = {
  gold: "border-gold/35 bg-gold/12 text-gold",
  moss: "border-emerald-700/40 bg-moss/25 text-emerald-200",
  crimson: "border-crimson/40 bg-crimson/20 text-red-200",
  muted: "border-border bg-ink/50 text-muted",
} as const;

export function IconBox({
  icon: Icon,
  tone = "gold",
  size = "md",
  className = "",
}: {
  icon: LucideIcon;
  tone?: keyof typeof tones;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizes = {
    sm: "h-9 w-9 [&_svg]:h-4 [&_svg]:w-4",
    md: "h-11 w-11 [&_svg]:h-5 [&_svg]:w-5",
    lg: "h-14 w-14 [&_svg]:h-7 [&_svg]:w-7",
  };
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-xl border shadow-inner ${tones[tone]} ${sizes[size]} ${className}`}
      aria-hidden
    >
      <Icon />
    </span>
  );
}
