import type { ReactNode } from "react";

export function SidebarTabs<T extends string>({
  tabs,
  active,
  onChange,
  footer,
}: {
  tabs: { id: T; label: string; icon?: ReactNode; count?: number }[];
  active: T;
  onChange: (id: T) => void;
  footer?: ReactNode;
}) {
  return (
    <div className="flex shrink-0 flex-col">
      <nav className="flex flex-1 flex-col gap-0.5 p-2" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-base font-medium transition ${
              active === tab.id
                ? "border border-gold/25 bg-gold/15 text-gold shadow-sm shadow-gold/10"
                : "text-muted hover:bg-white/5 hover:text-parchment"
            }`}
          >
            {tab.icon}
            <span className="min-w-0 flex-1 truncate">{tab.label}</span>
            {tab.count != null && tab.count > 0 && (
              <span className="shrink-0 rounded-full bg-ink/80 px-2 py-0.5 text-xs tabular-nums text-gold">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
      {footer != null && (
        <div className="shrink-0 border-t border-border p-2">{footer}</div>
      )}
    </div>
  );
}
