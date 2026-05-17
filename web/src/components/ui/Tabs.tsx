export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div
      role="tablist"
      className="flex flex-wrap gap-1 rounded-lg border border-border bg-ink/40 p-1"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`rounded-md px-4 py-2 text-sm font-medium transition ${
            active === tab.id
              ? "bg-gold text-ink shadow"
              : "text-muted hover:text-parchment"
          }`}
        >
          {tab.label}
          {tab.count != null && tab.count > 0 && (
            <span className="ml-1.5 opacity-70">({tab.count})</span>
          )}
        </button>
      ))}
    </div>
  );
}
