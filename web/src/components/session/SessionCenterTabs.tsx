import type { ReactNode } from "react";
import { MessageSquare, ScrollText, User } from "lucide-react";

export type SessionTab = "recap" | "chat";

export function SessionCenterTabs({
  active,
  onChange,
  sheetOpen,
}: {
  active: SessionTab;
  onChange: (tab: SessionTab) => void;
  sheetOpen?: boolean;
}) {
  const tabs: { id: SessionTab; label: string; icon: ReactNode }[] = [
    { id: "recap", label: "Recap", icon: <ScrollText className="h-4 w-4 shrink-0" /> },
    { id: "chat", label: "Chat", icon: <MessageSquare className="h-4 w-4 shrink-0" /> },
  ];

  return (
    <div
      role="tablist"
      className="flex shrink-0 items-center gap-1 border-b border-border bg-surface/60 px-4 py-2 sm:px-6 md:px-8"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id && !sheetOpen}
          onClick={() => onChange(tab.id)}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-base font-medium transition ${
            active === tab.id && !sheetOpen
              ? "bg-gold text-ink shadow-md shadow-gold/25"
              : "text-muted hover:bg-white/5 hover:text-parchment"
          }`}
        >
          {tab.icon}
          {tab.label}
        </button>
      ))}
      {sheetOpen && (
        <span className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-gold/30 bg-gold/10 px-3 py-1.5 text-sm font-medium text-gold">
          <User className="h-4 w-4" aria-hidden />
          Character sheet
        </span>
      )}
    </div>
  );
}
