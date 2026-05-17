export function Badge({
  children,
  tone = "gold",
}: {
  children: React.ReactNode;
  tone?: "gold" | "moss" | "muted";
}) {
  const tones = {
    gold: "bg-gold/15 text-gold border-gold/30",
    moss: "bg-moss/30 text-emerald-200 border-emerald-700/50",
    muted: "bg-white/5 text-muted border-border",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
