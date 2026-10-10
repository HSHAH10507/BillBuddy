import { Bot, Info, Stethoscope } from "lucide-react";
import type { CodeExplanation, PriceCheck } from "../types";
import { money } from "../lib";

interface Props {
  pricing: PriceCheck[];
  pricingSource: string | null;
  explanations: Record<string, CodeExplanation> | null; // null while loading
}

function RatioBadge({ p }: { p: PriceCheck }) {
  if (p.ratio == null) return <span className="text-xs text-muted">No benchmark</span>;
  const cls = p.level === "high" ? "bg-review-soft text-review ring-review/30" : "bg-match-soft text-match ring-match/20";
  return <span className={`num rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${cls}`}>{p.ratio}× Medicare</span>;
}

export default function ServicesExplained({ pricing, pricingSource, explanations }: Props) {
  if (!pricing.length) return null;
  const usedGemini = explanations && Object.values(explanations).some((e) => e.source === "gemini");

  return (
    <section className="rise rounded-2xl bg-card shadow-sm ring-1 ring-line">
      <header className="border-b border-line px-6 py-4">
        <h2 className="flex items-center gap-2 font-display text-2xl"><Stethoscope size={20} className="text-muted" /> Your services, explained</h2>
        <p className="text-sm text-muted">What each billing code means, and how the charge compares with what Medicare pays for the same service.</p>
      </header>

      <ul className="divide-y divide-line">
        {pricing.map((p) => {
          const ex = explanations?.[p.code];
          return (
            <li key={`${p.code}-${p.billed}`} className="grid gap-3 px-6 py-4 md:grid-cols-[minmax(0,1fr)_auto]">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="num rounded bg-paper px-1.5 py-0.5 text-xs ring-1 ring-line">{p.code}</span>
                  <span className="font-medium">{p.description}</span>
                </p>
                {explanations === null ? (
                  <div className="mt-2 h-4 w-3/4 animate-pulse rounded bg-paper" aria-label="Loading explanation" />
                ) : ex ? (
                  <p className="mt-1.5 text-sm">{ex.text}</p>
                ) : (
                  <p className="mt-1.5 text-sm text-muted">No plain-English explanation available for this code.</p>
                )}
                <p className="mt-1.5 text-xs text-muted">{p.note}</p>
              </div>
              <div className="flex items-center gap-4 md:flex-col md:items-end md:gap-1.5">
                <div className="num text-right text-sm">
                  <span className="text-muted">Billed </span>{money(p.billed)}
                  {p.medicare_rate != null && <><span className="text-muted"> · Medicare </span>{money(p.medicare_rate)}</>}
                </div>
                <RatioBadge p={p} />
              </div>
            </li>
          );
        })}
      </ul>

      <footer className="space-y-1.5 border-t border-line px-6 py-3 text-xs text-muted">
        {usedGemini && <p className="flex items-center gap-1.5"><Bot size={13} /> Explanations written by Gemini in plain English. They describe the service, not your diagnosis.</p>}
        <p className="flex items-start gap-1.5">
          <Info size={13} className="mt-0.5 shrink-0" />
          <span>
            Medicare rates: {pricingSource}. Private insurance usually pays more than Medicare, so this is a reference point,
            not a "fair price." Lab tests use a separate Medicare schedule and aren't compared yet.
          </span>
        </p>
      </footer>
    </section>
  );
}
