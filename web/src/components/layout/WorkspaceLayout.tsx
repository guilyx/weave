import type { ReactNode } from "react";

/**
 * Full-height workspace: left rail, scrollable main, optional right aside.
 * On small screens: rail on top, main, then aside (journal) with fixed slice of height.
 */
export function WorkspaceLayout({
  sidebar,
  children,
  aside,
  className = "",
}: {
  sidebar: ReactNode;
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex h-full min-h-0 w-full flex-col overflow-hidden md:flex-row ${className}`}
    >
      <aside className="flex max-h-[44%] shrink-0 flex-col border-b border-border bg-surface/80 md:max-h-none md:w-[15.5rem] md:shrink-0 md:border-b-0 md:border-r lg:w-[16.5rem]">
        {sidebar}
      </aside>
      <div className="flex min-h-0 min-w-0 flex-[1_1_50%] flex-col overflow-hidden">
        {children}
      </div>
      {aside != null && (
        <aside className="flex h-[min(42dvh,380px)] shrink-0 flex-col border-t border-border bg-surface/60 md:h-auto md:min-h-0 md:w-[min(30rem,38vw)] md:max-w-[34rem] md:shrink-0 md:border-t-0 md:border-l lg:w-[32rem]">
          {aside}
        </aside>
      )}
    </div>
  );
}
