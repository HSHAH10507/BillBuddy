import { BookOpen } from "lucide-react";
import type { GlossaryTerm } from "../types";

export default function Glossary({ terms }: { terms: GlossaryTerm[] }) {
  return (
    <section className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
      <h2 className="flex items-center gap-2 font-display text-2xl"><BookOpen size={20} className="text-muted" /> Insurance terms, in plain English</h2>
      <p className="text-sm text-muted">General definitions, applied to your documents. Your plan details are the final word.</p>
      <dl className="mt-5 grid gap-x-8 gap-y-5 md:grid-cols-2">
        {terms.map((t) => (
          <div key={t.term} className="border-l-2 border-line pl-4">
            <dt className="font-semibold">{t.term}</dt>
            <dd className="mt-1 text-sm text-muted">{t.definition}</dd>
            {t.in_your_documents && <dd className="mt-2 text-sm"><span className="font-medium text-match">In your documents: </span>{t.in_your_documents}</dd>}
          </div>
        ))}
      </dl>
    </section>
  );
}
