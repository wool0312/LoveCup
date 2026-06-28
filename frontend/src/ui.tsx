import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Card({ children, className = "", ...props }: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div
      className={`rounded-lg border border-emerald-900/10 bg-white/95 p-4 shadow-sm shadow-emerald-900/5 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "soft" }) {
  const styles = {
    primary: "bg-brand text-white hover:bg-cup-deep disabled:bg-slate-300",
    ghost: "bg-transparent text-slate-600 hover:bg-emerald-50",
    soft: "bg-emerald-50 text-brand hover:bg-emerald-100 disabled:opacity-50",
  }[variant];
  return (
    <button
      className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  );
}

export function Pill({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: "slate" | "green" | "rose" | "amber";
}) {
  const styles = {
    slate: "bg-slate-100 text-slate-600",
    green: "bg-emerald-100 text-emerald-700",
    rose: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
  }[tone];
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${styles}`}>
      {children}
    </span>
  );
}

export function Field({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-500">{label}</span>
      {children}
    </label>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand"
      {...props}
    />
  );
}

export function Banner({ tone, children }: { tone: "error" | "info" | "success"; children: ReactNode }) {
  const styles = {
    error: "bg-rose-50 text-rose-700 border-rose-200",
    info: "bg-emerald-50 text-emerald-800 border-emerald-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  }[tone];
  return <div className={`rounded-lg border px-3 py-2 text-sm ${styles}`}>{children}</div>;
}
