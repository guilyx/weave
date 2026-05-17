import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders Weave chat replies (Markdown from the agent).
 */
export function ChatMarkdown({
  content,
  className = "",
}: {
  content: string;
  className?: string;
}) {
  if (!content.trim()) return null;

  return (
    <div className={`prose-chat ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-gold underline decoration-gold/40 hover:decoration-gold"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          code: ({ className: codeClass, children, ...props }) => {
            const inline = !codeClass;
            if (inline) {
              return (
                <code
                  className="rounded bg-surface-raised/90 px-1.5 py-0.5 font-mono text-sm text-gold/95"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code
                className={`block overflow-x-auto rounded-lg border border-border/60 bg-ink/80 p-3 font-mono text-sm text-parchment/90 ${codeClass ?? ""}`}
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-3 overflow-x-auto rounded-lg">{children}</pre>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
