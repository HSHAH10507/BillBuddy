import { ArrowRight, Bot, Calculator } from "lucide-react";
import type { AnalysisResult } from "../types";
import { money } from "../lib";

export default function SummaryHeader({ data }: { data: AnalysisResult }) {
  const billDue = data.bill.totals.patient_responsibility;
  const eobOwe = data.eob.totals.patient_responsibility;
  const gap = billDue != null && eobOwe != null ? billDue - eobOwe : null;
  const s = data.stats;
  const total = s.matched + s.mismatched + s.bill_only + s.eob_only || 1;
  const segments = [
    { n: s.matched, label: "matched", cls: "bg-match" },
    { n: s.mismatched, label: "matched with differences", cls: "bg-review" },
    { n: s.bill_only, label: "only on bill", cls: "bg-missing" },
    { n: s.eob_only, label: "only on EOB", cls: "bg-eob" },
  ];

  return (
    <section className="rise grid gap-4 lg:grid-cols-5">
      <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line lg:col-span-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted">What you're asked to pay</p>
        <div className="mt-3 flex flex-wrap items-end gap-x-6 gap-y-3">
          <div>
            <p className="text-sm text-muted">Bill says</p>
            <p className="num text-3xl font-medium text-bill">{money(billDue)}</p>
          </div>
          <ArrowRight className="mb-2 text-muted" size={20} aria-hidden />
          <div>
            <p className="text-sm text-muted">EOB says you may owe</p>
            <p className="num text-3xl font-medium text-eob">{money(eobOwe)}</p>
          </div>
          {gap != null && Math.abs(gap) > 0.005 && (
            <div className="ml-auto rounded-xl bg-review-soft px-4 py-2 text-review">
              <p className="text-xs font-semibold uppercase tracking-wide">Gap</p>
              <p className="num text-2xl font-medium">{money(Math.abs(gap))}</p>
            </div>
          )}
        </div>
        <p className="mt-5 leading-relaxed">{data.summary}</p>
        <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted">
          {data.summary_source === "gemini" ? <Bot size={14} /> : <Calculator size={14} />}
          {data.summary_source === "gemini"
            ? "Summary written by Gemini from the rule-based findings below"
            : "Summary generated from the rule-based findings below"}
        </p>
      </div>

      <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line lg:col-span-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted">Line-by-line</p>
        <p className="mt-3 font-display text-3xl">
          {s.matched} <span className="text-lg text-muted">of {total} matched cleanly</span>
        </p>
        <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-paper" role="img"
          aria-label={segments.map((g) => `${g.n} ${g.label}`).join(", ")}>
          {segments.map((g) => g.n > 0 && (
            <div key={g.label} className={`${g.cls} h-full border-r-2 border-card last:border-r-0`} style={{ width: `${(g.n / total) * 100}%` }} />
          ))}
        </div>
        <ul className="mt-4 grid grid-cols-2 gap-2 text-sm">
          {segments.map((g) => (
            <li key={g.label} className="flex items-center gap-2">
              <span className={`size-2.5 rounded-full ${g.cls}`} />
              <span className="num">{g.n}</span>
              <span className="text-muted">{g.label}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 border-t border-line pt-3 text-sm">
          <span className="num font-medium">{s.review_findings}</span>{" "}
          <span className="text-muted">item{s.review_findings === 1 ? "" : "s"} flagged for a human to review</span>
        </p>
      </div>
    </section>
  );
}
