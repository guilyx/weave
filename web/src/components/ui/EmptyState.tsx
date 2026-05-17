import type { LucideIcon } from "lucide-react";
import { IconBox } from "./IconBox";

export function EmptyState({
  icon,
  title,
  children,
  className = "",
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col items-center px-6 py-10 text-center ${className}`}>
      <IconBox icon={icon} size="lg" className="mb-4 opacity-90" />
      <h3 className="font-display text-xl font-semibold text-parchment">{title}</h3>
      <p className="mt-3 max-w-md text-base leading-relaxed text-muted">{children}</p>
    </div>
  );
}
