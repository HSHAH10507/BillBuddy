import { CalendarClock, CalendarPlus, ExternalLink, Phone, Receipt, Scale } from "lucide-react";
import type { Deadline } from "../types";
import { daysUntil, downloadCalendar, shortDate } from "../lib";

const ICON: Record<Deadline["kind"], React.ReactNode> = {
  followup: <Phone size={16} />,
  payment: <Receipt size={16} />,
  appeal: <Scale size={16} />,
};

function DaysBadge({ iso }: { iso: string }) {
  const n = daysUntil(iso);
  const [label, cls] =
    n < 0 ? [`${Math.abs(n)} day${n === -1 ? "" : "s"} ago`, "bg-missing-soft text-missing"]
      : n === 0 ? ["Today", "bg-review-soft text-review"]
        : n <= 14 ? [`In ${n} day${n === 1 ? "" : "s"}`, "bg-review-soft text-review"]
          : [`In ${n} days`, "bg-match-soft text-match"];
  return <span className={`num whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{label}</span>;
}

export default function Deadlines({ deadlines }: { deadlines: Deadline[] }) {
  if (!deadlines.length) return null;
  return (
    <section className="rise rounded-2xl bg-card shadow-sm ring-1 ring-line">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-line px-6 py-4">
        <div>
          <h2 className="flex items-center gap-2 font-display text-2xl"><CalendarClock size={20} className="text-muted" /> Important dates</h2>
          <p className="text-sm text-muted">Dates from your documents, plus suggested reminders.</p>
        </div>
        <button type="button" onClick={() => downloadCalendar(deadlines)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-card px-3 py-2 text-sm font-medium ring-1 ring-line hover:bg-paper">
          <CalendarPlus size={15} /> Add all to calendar
        </button>
      </header>
      <ol className="divide-y divide-line">
        {deadlines.map((d) => (
          <li key={d.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-start">
            <div className="flex w-40 shrink-0 items-center gap-3">
              <span className="grid size-9 place-items-center rounded-lg bg-paper text-muted ring-1 ring-line">{ICON[d.kind]}</span>
              <span className="num whitespace-nowrap text-sm font-medium">{shortDate(d.date)}</span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2 font-semibold">
                {d.title}
                {d.estimated && d.kind !== "appeal" && <span className="rounded bg-paper px-1.5 py-0.5 text-[11px] font-medium text-muted ring-1 ring-line">suggested</span>}
              </p>
              <p className="mt-1 text-sm text-muted">{d.description}</p>
              {d.source && (
                <a href={d.source} target="_blank" rel="noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-xs text-muted underline underline-offset-4 hover:text-ink">
                  How appeals work <ExternalLink size={11} />
                </a>
              )}
            </div>
            <div className="flex items-center gap-2 sm:flex-col sm:items-end">
              <DaysBadge iso={d.date} />
              <button type="button" onClick={() => downloadCalendar([d], `BillBuddy_${d.id}.ics`)}
                className="inline-flex items-center gap-1 text-xs text-muted hover:text-ink" aria-label={`Add "${d.title}" to calendar`}>
                <CalendarPlus size={13} /> Add to calendar
              </button>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
