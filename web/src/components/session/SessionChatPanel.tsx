import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image, Loader2, Map, MessageSquare, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type SessionMessage } from "../../api";
import { ChatMarkdown } from "../chat/ChatMarkdown";
import { Button } from "../ui/Button";
import { Card, CardTitle } from "../ui/Card";
import { IconBox } from "../ui/IconBox";
import { Input } from "../ui/Input";

const PROMPTS = [
  { icon: Map, label: "Describe a battle map for this scene" },
  { icon: Image, label: "Portrait idea for the NPC we just met" },
];

export function SessionChatPanel({
  sessionId,
  className = "",
}: {
  sessionId: string;
  className?: string;
}) {
  const qc = useQueryClient();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: () => api.listMessages(sessionId),
  });

  const send = useMutation({
    mutationFn: () => api.postMessage(sessionId, input),
    onSuccess: () => {
      setInput("");
      void qc.invalidateQueries({ queryKey: ["messages", sessionId] });
      void qc.invalidateQueries({ queryKey: ["activity", sessionId] });
    },
  });

  const thread = messages.data ?? [];

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [thread.length, send.isPending]);

  return (
    <Card
      className={`flex h-full min-h-0 flex-col overflow-hidden p-0 ${className}`}
    >
      <div className="shrink-0 border-b border-border px-5 py-4">
        <div className="flex items-start gap-3">
          <IconBox icon={MessageSquare} size="sm" />
          <div>
            <CardTitle className="mb-1 text-xl">Ask Weave</CardTitle>
            <p className="text-sm leading-relaxed text-muted">
              Rules, lore, recap — or map / scene / portrait briefs (text until images ship).
            </p>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-b border-border/60 px-5 py-3">
        {PROMPTS.map(({ icon: Icon, label }) => (
          <button
            key={label}
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-ink/40 px-3 py-1.5 text-sm text-parchment transition hover:border-gold/40 hover:bg-gold/5"
            onClick={() => setInput(label)}
          >
            <Icon className="h-4 w-4 text-gold" />
            {label}
          </button>
        ))}
      </div>

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4"
      >
        {thread.length === 0 && !send.isPending && (
          <p className="text-center text-sm text-muted">
            Ask a question — answers appear formatted below.
          </p>
        )}
        {thread.map((msg: SessionMessage) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[92%] rounded-xl border px-4 py-3 ${
                  isUser
                    ? "border-gold/25 bg-gold/10"
                    : "border-border/70 bg-ink/50"
                }`}
              >
                <p
                  className={`mb-2 text-xs font-semibold uppercase tracking-wider ${
                    isUser ? "text-gold/90" : "text-gold"
                  }`}
                >
                  {isUser ? "You" : "Weave"}
                </p>
                {isUser ? (
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-parchment/95">
                    {msg.content}
                  </p>
                ) : (
                  <ChatMarkdown content={msg.content} />
                )}
              </div>
            </div>
          );
        })}
        {send.isPending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-xl border border-border/70 bg-ink/50 px-4 py-3 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin text-gold" />
              Weave is thinking…
            </div>
          </div>
        )}
      </div>

      <div className="flex shrink-0 gap-3 border-t border-border p-5">
        <Input
          className="flex-1"
          placeholder="Question, map brief, scene paint-over…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && input.trim() && send.mutate()}
        />
        <Button
          className="shrink-0 px-5"
          disabled={!input.trim() || send.isPending}
          onClick={() => send.mutate()}
        >
          {send.isPending ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
    </Card>
  );
}
