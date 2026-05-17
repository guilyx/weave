import { Dices } from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";

export function AppShell() {
  const { pathname } = useLocation();
  const isSession = /\/sessions\/[^/]+$/.test(pathname);

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <header className="z-50 shrink-0 border-b border-border/80 bg-ink/95 backdrop-blur-md">
        <div className="flex items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link
            to="/"
            className="flex items-center gap-2.5 text-parchment no-underline hover:text-gold"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-gold/40 bg-gold/10 text-gold">
              <Dices className="h-5 w-5" aria-hidden />
            </span>
            <span className="hidden sm:block">
              <span className="font-display text-xl font-semibold tracking-wide">
                Weave
              </span>
              <span className="block text-xs leading-tight text-muted">
                Session assistant
              </span>
            </span>
          </Link>
          <nav className="flex items-center gap-2">
            <Link
              to="/"
              className="rounded-md px-3 py-2 text-base text-muted no-underline hover:bg-white/5 hover:text-parchment"
            >
              Campaigns
            </Link>
            <Link
              to="/campaigns/new"
              className="rounded-lg bg-gold px-4 py-2 text-base font-semibold text-ink no-underline shadow shadow-gold/20 hover:bg-gold-bright"
            >
              New
            </Link>
          </nav>
        </div>
      </header>
      <main className="min-h-0 flex-1 overflow-hidden">
        <div
          className={
            isSession ? "h-full" : "mx-auto h-full max-w-6xl overflow-hidden px-4 sm:px-6"
          }
        >
          <Outlet />
        </div>
      </main>
    </div>
  );
}
