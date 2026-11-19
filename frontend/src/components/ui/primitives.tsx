import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

export function Card({
  className,
  interactive = false,
  children,
}: {
  className?: string;
  interactive?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "glass-card rounded-2xl p-4 sm:p-6 transition-all duration-200",
        interactive && "hover:border-[#D4AF37]/40 hover:-translate-y-[1px] hover:bg-[#17171D]/90",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}) {
  const variants = {
    primary:
      "bg-gradient-to-b from-[#E5C66B] via-[#D4AF37] to-[#BF9628] text-[#0B0B0D] font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.4),0_8px_22px_-6px_rgba(212,175,55,0.45)] hover:brightness-105 active:scale-[0.985]",
    secondary:
      "bg-white/[0.05] text-[#F5F5F7] border border-white/14 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] hover:bg-white/[0.1] hover:border-white/25 active:scale-[0.985]",
    ghost: "bg-transparent text-[#9A9AA6] hover:text-[#F5F5F7] hover:bg-white/[0.06]",
    danger:
      "bg-rose-500/15 text-rose-200 border border-rose-500/35 hover:bg-rose-500/25 active:scale-[0.985]",
  };
  const sizes = {
    sm: "min-h-[38px] px-3.5 py-1.5 text-xs rounded-xl",
    md: "min-h-[44px] px-4.5 py-2.5 text-sm rounded-xl",
    lg: "min-h-[50px] px-6 py-3 text-base rounded-2xl",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37]/60 disabled:opacity-45 disabled:pointer-events-none cursor-pointer",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}

export function Badge({
  className,
  tone = "neutral",
  children,
}: {
  className?: string;
  tone?: "gold" | "emerald" | "amber" | "rose" | "sky" | "neutral";
  children: React.ReactNode;
}) {
  const tones = {
    gold: "bg-[#D4AF37]/15 text-[#E8D5B5] border-[#D4AF37]/35",
    emerald: "bg-emerald-500/12 text-emerald-300 border-emerald-500/30",
    amber: "bg-amber-500/12 text-amber-200 border-amber-500/30",
    rose: "bg-rose-500/12 text-rose-200 border-rose-500/30",
    sky: "bg-sky-500/12 text-sky-200 border-sky-500/30",
    neutral: "bg-white/[0.06] text-[#9A9AA6] border-white/12",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full min-h-[44px] rounded-xl bg-[#0D0D11] border border-white/12 px-3.5 py-2.5 text-sm text-[#F5F5F7] shadow-[inset_0_2px_4px_rgba(0,0,0,0.4)] placeholder:text-[#6E6E7A] focus:outline-none focus:border-[#D4AF37]/75 focus:ring-2 focus:ring-[#D4AF37]/20 transition-all",
        className
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full min-h-[44px] rounded-xl bg-[#0D0D11] border border-white/12 px-3.5 py-2.5 text-sm text-[#F5F5F7] shadow-[inset_0_2px_4px_rgba(0,0,0,0.4)] focus:outline-none focus:border-[#D4AF37]/75 focus:ring-2 focus:ring-[#D4AF37]/20 transition-all",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-xl bg-[#0D0D11] border border-white/12 px-3.5 py-2.5 text-sm text-[#F5F5F7] shadow-[inset_0_2px_4px_rgba(0,0,0,0.4)] placeholder:text-[#6E6E7A] focus:outline-none focus:border-[#D4AF37]/75 focus:ring-2 focus:ring-[#D4AF37]/20 transition-all",
        className
      )}
      {...props}
    />
  );
}

export function FieldLabel({
  children,
  required,
  hint,
}: {
  children: React.ReactNode;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div className="mb-1.5 flex items-baseline justify-between gap-2">
      <label className="text-[11px] font-semibold uppercase tracking-wider text-[#9A9AA6]">
        {children}
        {required && <span className="ml-1 text-[#D4AF37]">*</span>}
      </label>
      {hint && <span className="text-[11px] text-[#6E6E7A]">{hint}</span>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton-shimmer rounded-xl", className)} />;
}

export function SectionHeader({
  icon,
  title,
  subtitle,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
      <div>
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-base font-semibold tracking-tight text-[#F5F5F7]">{title}</h2>
        </div>
        {subtitle && <p className="mt-0.5 text-xs text-[#9A9AA6]">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
