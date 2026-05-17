import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

const field =
  "w-full rounded-lg border border-border bg-ink/60 px-3.5 py-3 text-base text-parchment placeholder:text-muted/70 focus:border-gold/60 focus:outline-none focus:ring-2 focus:ring-gold/20";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${field} ${className}`} {...props} />;
}

export function Textarea({
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`${field} min-h-[100px] resize-y ${className}`}
      {...props}
    />
  );
}

export function Label({
  children,
  htmlFor,
}: {
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted"
    >
      {children}
    </label>
  );
}
