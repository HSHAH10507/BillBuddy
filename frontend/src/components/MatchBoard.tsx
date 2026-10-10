import { AlertTriangle, CheckCircle2, CircleSlash, Link2 } from "lucide-react";
import type { AnalysisResult, LineItem, MatchPair, MatchStatus } from "../types";
import { money, shortDate } from "../lib";

const STATUS: Record<MatchStatus, { label: string; cls: string; icon: React.ReactNode }> = {
  match: { label: "Matched", cls: "bg-match-soft text-match", icon: <CheckCircle2 size={14} /> },
  mismatch: { label: "Differs", cls: "bg-review-soft text-review", icon: <AlertTriangle size={14} /> },
  bill_only: { label: "Bill only", cls: "bg-missing-soft text-missing", icon: <CircleSlash size={14} /> },
  eob_only: { label: "EOB only", cls: "bg-eob-soft text-eob", icon: <CircleSlash size={14} /> },
};

function Flag({ on, children }: { on: boolean; children: React.ReactNode }) {
  return on ? <mark className="rounded bg-review-soft px-1 text-review ring-1 ring-review/30">{children}</mark> : <>{children}</>;
}

function ItemCard({ item, side, diffs }: { item: LineItem; side: "bill" | "eob"; diffs: string[] }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2 text-xs text-muted">
        <Flag on={diffs.includes("service_date")}>{shortDate(item.service_date)}</Flag>
        {item.code && <span className="num rounded bg-paper px-1.5 py-0.5 ring-1 ring-line"><Flag on={diffs.includes("code")}>{item.code}</Flag></span>}
      </div>
      <p className="mt-1 truncate text-sm font-medium" title={item.description}>{item.description}</p>
      {side === "bill" ? (
        <p className="num mt-1 text-sm">Charge <Flag on={diffs.includes("billed")}>{money(item.billed)}</Flag></p>
      ) : (
        <p className="num mt-1 flex flex-wrap gap-x-3 text-xs text-muted">
          <span>Billed <span className="text-ink"><Flag on={diffs.includes("billed")}>{money(item.billed)}</Flag></span></span>
          <span>Allowed <span className="text-ink">{money(item.allowed)}</span></span>
          <span>You owe <span className="text-ink">{money(item.patient_responsibility)}</span></span>
        </p>
      )}
    </div>
  );
}

function Missing({ text }: { text: string }) {
  return <div className="grid h-full place-items-center rounded-lg border border-dashed border-missing/40 px-3 py-4 text-center text-xs text-missing">{text}</div>;
}

interface Props {
  data: AnalysisResult;
  focus: string[];
  onSelect: (itemIds: string[]) => void;
}

export default function MatchBoard({ data, focus, onSelect }: Props) {
  const bills = new Map(data.bill.line_items.map((i) => [i.id, i]));
  const eobs = new Map(data.eob.line_items.map((i) => [i.id, i]));
  const flagged = new Set(data.findings.flatMap((f) => f.related_items));
  const ids = (m: MatchPair) => [m.bill_item_id, m.eob_item_id].filter(Boolean) as string[];

  return (
    <section className="rise rounded-2xl bg-card shadow-sm ring-1 ring-line">
      <header className="flex flex-wrap items-end justify-between gap-2 border-b border-line px-6 py-4">
        <div>
          <h2 className="font-display text-2xl">Charge matching</h2>
          <p className="text-sm text-muted">Paired by billing code, date, description and amount — even when the wording differs.</p>
        </div>
        <div className="hidden grid-cols-2 gap-24 pr-6 text-xs font-semibold uppercase tracking-widest sm:grid">
          <span className="text-bill">Bill</span><span className="text-eob">EOB</span>
        </div>
      </header>
      <ul className="divide-y divide-line">
        {data.matches.map((m, idx) => {
          const b = m.bill_item_id ? bills.get(m.bill_item_id) : undefined;
          const e = m.eob_item_id ? eobs.get(m.eob_item_id) : undefined;
          const st = STATUS[m.status];
          const isFocus = ids(m).some((id) => focus.includes(id));
          const clickable = ids(m).some((id) => flagged.has(id));
          return (
            <li key={idx}>
              <button
                type="button"
                disabled={!clickable}
                onClick={() => onSelect(ids(m))}
                className={`grid w-full grid-cols-1 items-center gap-3 px-6 py-4 text-left transition sm:grid-cols-[1fr_auto_1fr]
                  ${isFocus ? "bg-review-soft/50" : clickable ? "hover:bg-paper/70" : "cursor-default"}`}
              >
                {b ? <ItemCard item={b} side="bill" diffs={m.differences} /> : <Missing text="No matching line on the bill" />}
                <div className="flex flex-col items-center gap-1">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${st.cls}`}>{st.icon}{st.label}</span>
                  {m.score > 0 && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-muted" title={m.reasons.join(" · ")}>
                      <Link2 size={11} /> {m.reasons.length} signal{m.reasons.length === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
                {e ? <ItemCard item={e} side="eob" diffs={m.differences} /> : <Missing text="No matching line on the EOB" />}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-line px-6 py-3 text-xs text-muted">Click a highlighted row to jump to its finding. Hover “signals” to see why two lines were paired.</p>
    </section>
  );
}
