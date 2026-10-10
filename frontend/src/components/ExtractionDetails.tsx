import { Fragment } from "react";
import { ChevronDown, ScanText } from "lucide-react";
import type { ExtractedDocument } from "../types";
import { money, shortDate } from "../lib";

function DocDetails({ doc }: { doc: ExtractedDocument }) {
  const isEob = doc.doc_type === "eob";
  const meta: [string, string | null][] = [
    ["File", doc.filename], ["Read with", doc.extraction_method], [isEob ? "Insurer" : "Provider", isEob ? doc.insurer : doc.provider],
    ["Patient", doc.patient], ["Claim #", doc.claim_id], ["Account #", doc.account_id],
  ];
  return (
    <div className="min-w-0">
      <h4 className={`text-xs font-semibold uppercase tracking-widest ${isEob ? "text-eob" : "text-bill"}`}>{isEob ? "EOB" : "Bill"}</h4>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {meta.filter(([, v]) => v).map(([k, v]) => (<Fragment key={k}><dt className="text-muted">{k}</dt><dd className="truncate">{v}</dd></Fragment>))}
      </dl>
      <div className="mt-3 overflow-x-auto">
        <table className="num w-full text-xs">
          <thead className="text-left text-muted">
            <tr><th className="py-1 pr-2 font-medium">Date</th><th className="pr-2 font-medium">Code</th><th className="pr-2 font-medium">Billed</th>
              {isEob && <><th className="pr-2 font-medium">Allowed</th><th className="pr-2 font-medium">Plan paid</th><th className="font-medium">You owe</th></>}</tr>
          </thead>
          <tbody className="divide-y divide-line">
            {doc.line_items.map((i) => (
              <tr key={i.id}><td className="py-1 pr-2">{shortDate(i.service_date)}</td><td className="pr-2">{i.code ?? "—"}</td><td className="pr-2">{money(i.billed)}</td>
                {isEob && <><td className="pr-2">{money(i.allowed)}</td><td className="pr-2">{money(i.plan_paid)}</td><td>{money(i.patient_responsibility)}</td></>}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {doc.warnings.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs text-review">{doc.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-muted hover:text-ink">Show raw extracted text</summary>
        <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-paper p-3 text-[11px] leading-relaxed">{doc.raw_text}</pre>
      </details>
    </div>
  );
}

export default function ExtractionDetails({ bill, eob }: { bill: ExtractedDocument; eob: ExtractedDocument }) {
  return (
    <details className="group rounded-2xl bg-card shadow-sm ring-1 ring-line">
      <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4">
        <span className="flex items-center gap-2 font-display text-xl"><ScanText size={20} className="text-muted" /> How BillBuddy read your documents</span>
        <ChevronDown className="transition group-open:rotate-180" size={18} />
      </summary>
      <div className="grid gap-8 border-t border-line px-6 py-5 md:grid-cols-2">
        <DocDetails doc={bill} />
        <DocDetails doc={eob} />
      </div>
    </details>
  );
}
