import type { ReactNode } from "react";
import {
  SessionCenterTabs,
  type SessionTab,
} from "../session/SessionCenterTabs";

/** Full-height center column between session sidebars. */
export function SessionMainArea({
  tab,
  onTabChange,
  sheetOpen,
  children,
}: {
  tab: SessionTab;
  onTabChange: (tab: SessionTab) => void;
  sheetOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-ink/10">
      <SessionCenterTabs active={tab} onChange={onTabChange} sheetOpen={sheetOpen} />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4 sm:px-6 sm:py-5 md:px-8 lg:px-10">
        <div className="flex h-full min-h-0 w-full flex-col">{children}</div>
      </div>
    </div>
  );
}
