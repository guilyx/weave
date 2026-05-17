import { useQuery } from "@tanstack/react-query";
import { BookOpen, ChevronRight, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card } from "../components/ui/Card";

export default function CampaignListPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["campaigns"],
    queryFn: api.listCampaigns,
  });

  return (
    <div className="h-full overflow-y-auto py-3">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-parchment">
            Your campaigns
          </h1>
          <p className="mt-2 max-w-xl text-muted">
            Each campaign holds your party&apos;s D&amp;D Beyond sheets, lore, and
            live session history.
          </p>
        </div>
        <Link
          to="/campaigns/new"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-gold px-5 py-2.5 text-sm font-semibold text-ink no-underline shadow-lg shadow-gold/20 hover:bg-gold-bright"
        >
          <Plus className="h-4 w-4" />
          New campaign
        </Link>
      </div>

      {isLoading && <p className="text-muted">Loading campaigns…</p>}
      {error && (
        <p className="rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-red-300">
          {(error as Error).message}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data?.map((c) => (
          <Link
            key={c.id}
            to={`/campaigns/${c.id}`}
            className="group no-underline"
          >
            <Card className="h-full transition group-hover:border-gold/40 group-hover:shadow-gold/10">
              <div className="flex items-start justify-between gap-3">
                <div className="flex gap-3">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-border bg-ink text-gold">
                    <BookOpen className="h-5 w-5" />
                  </span>
                  <div>
                    <h2 className="font-display text-lg font-semibold text-parchment group-hover:text-gold">
                      {c.name}
                    </h2>
                    {c.description ? (
                      <p className="mt-1 line-clamp-2 text-sm text-muted">
                        {c.description}
                      </p>
                    ) : (
                      <p className="mt-1 text-sm italic text-muted/70">
                        No description
                      </p>
                    )}
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-gold" />
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {data?.length === 0 && !isLoading && (
        <Card className="text-center">
          <p className="text-muted">No campaigns yet.</p>
          <Link
            to="/campaigns/new"
            className="mt-4 inline-flex text-gold no-underline hover:underline"
          >
            Create your first campaign →
          </Link>
        </Card>
      )}
    </div>
  );
}
