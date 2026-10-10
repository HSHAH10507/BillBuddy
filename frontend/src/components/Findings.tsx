import { useState } from "react";
import { Check, Copy, HelpCircle, Info, MessageSquareQuote, SearchCheck } from "lucide-react";
import type { Evidence, Finding } from "../types";
import { money } from "../lib";

const DOC_BADGE: Record<Evidence["document"], string> = {
  bill: "bg-bill-soft text-bill",
  eob: "bg-eob-soft text-eob",
  computed: "bg-paper text-muted ring-1 ring-line",
};
const ASK_LABEL = { provider: "Ask your provider's billing office", insurer: "Ask your insurer", either: "Ask your provider or insurer" };

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { /* clipboard blocked */ }
      }}
      className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-card px-2.5 py-1.5 text-xs font-medium ring-1 ring-line hover:bg-paper"
    >
      {done ? <Check size={14} className="text-match" /> : <Copy size={14} />} {done ? "Copied" : "Copy"}
    </button>
  );
}

function FindingCard({ f, active, onFocus }: { f: Finding; active: boolean; onFocus: () => void }) {
  return (
    <article
      id={`finding-${f.id}`}
      onMouseEnter={onFocus}
      className={`scroll-mt-24 rounded-2xl bg-card p-6 shadow-sm ring-1 transition ${active ? "ring-2 ring-review" : "ring-line"}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className={`mt-0.5 rounded-full px-2.5 py-1 text-xs font-semibold ${f.severity === "review" ? "bg-review-soft text-review" : "bg-eob-soft text-eob"}`}>
            {f.severity === "review" ? "Needs review" : "Worth noting"}
          </span>
          <h3 className="font-display text-xl leading-snug">{f.title}</h3>
        </div>
        {f.amount_at_stake != null && f.amount_at_stake > 0 && (
          <p className="num rounded-lg bg-paper px-3 py-1 text-sm ring-1 ring-line">{money(f.amount_at_stake)} in question</p>
        )}
      </div>

      <p className="mt-3 leading-relaxed">{f.detected}</p>

      <div className="mt-4 overflow-hidden rounded-xl ring-1 ring-line">
        <p className="flex items-center gap-1.5 bg-paper px-4 py-2 text-xs font-semibold uppercase tracking-widest text-muted">
          <SearchCheck size={14} /> Evidence compared
        </p>
        <table className="w-full text-sm">
          <tbody className="divide-y divide-line">
            {f.evidence.map((ev, i) => (
              <tr key={i} className="align-top">
                <td className="w-24 px-4 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase ${DOC_BADGE[ev.document]}`}>{ev.document}</span>
                </td>
                <td className="px-2 py-2.5 text-muted">{ev.field}</td>
                <td className="num px-2 py-2.5">{ev.value}</td>
                <td className="hidden px-4 py-2.5 text-xs text-muted md:table-cell">{ev.location}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <dl className="mt-4 grid gap-4 text-sm md:grid-cols-2">
        <div>
          <dt className="flex items-center gap-1.5 font-semibold"><Info size={15} className="text-muted" /> Why it was flagged</dt>
          <dd className="mt-1 text-muted">{f.why_flagged}</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 font-semibold"><HelpCircle size={15} className="text-muted" /> What BillBuddy can't determine</dt>
          <dd className="mt-1 text-muted">{f.cannot_determine}</dd>
        </div>
      </dl>

      <div className="mt-4 rounded-xl bg-match-soft/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-match">
            <MessageSquareQuote size={14} /> {ASK_LABEL[f.ask]}
          </p>
          <CopyButton text={f.suggested_question} />
        </div>
        <p className="mt-2 italic">“{f.suggested_question}”</p>
      </div>
    </article>
  );
}

export default function Findings({ findings, activeIds, onFocus }: {
  findings: Finding[]; activeIds: string[]; onFocus: (ids: string[]) => void;
}) {
  if (!findings.length) {
    return (
      <section className="rounded-2xl bg-match-soft p-6 text-match">
        <h2 className="font-display text-2xl">Everything lines up</h2>
        <p className="mt-1">Every bill charge matched the EOB and all totals reconcile.</p>
      </section>
    );
  }
  return (
    <section className="space-y-4">
      <div>
        <h2 className="font-display text-2xl">What may need a human to review</h2>
        <p className="text-sm text-muted">
          These come from deterministic arithmetic and comparison rules, not an AI guess. Each one shows the values that triggered it.
        </p>
      </div>
      {findings.map((f) => (
        <FindingCard key={f.id} f={f} active={f.related_items.some((id) => activeIds.includes(id))} onFocus={() => onFocus(f.related_items)} />
      ))}
    </section>
  );
}
