import { Link } from "react-router-dom";
import { ArrowRight, Link2, MessageSquareQuote, SearchCheck, Upload } from "lucide-react";

const STEPS = [
  { icon: <Upload size={18} />, title: "Upload your documents",
    text: "Add the bill from your doctor or hospital and the Explanation of Benefits from your insurance company." },
  { icon: <Link2 size={18} />, title: "We line up every charge",
    text: "Each service on your bill is paired with the same service on your EOB, even when they describe it differently." },
  { icon: <SearchCheck size={18} />, title: "We check the numbers",
    text: "We look for charges that don't match, services billed twice, and totals that don't add up." },
  { icon: <MessageSquareQuote size={18} />, title: "You get clear answers",
    text: "Anything worth a second look is explained in plain English, with a question you can ask before you pay." },
];

const DISCLAIMERS = [
  "BillBuddy Health helps you prepare questions. It does not confirm billing errors and is not medical, legal or financial advice.",
  "Always check with your provider and insurance company before paying or disputing a bill.",
  "Some differences have good explanations, such as a prior balance or a charge from a different visit.",
  "Bills and EOBs come in many formats, so some documents may not be read correctly.",
  "Sample documents on this site are fictional. Uploaded files are analyzed and not stored.",
];

export default function AboutPage() {
  return (
    <div className="rise mx-auto max-w-3xl space-y-16 pb-8">
      <section>
        <p className="text-xs font-semibold uppercase tracking-widest text-match">About</p>
        <h1 className="mt-2 font-display text-4xl leading-tight sm:text-5xl">Making medical bills make sense.</h1>
        <p className="mt-5 text-lg text-muted">
          Medical bills and insurance statements are written for billing departments, not patients. When the bill
          from your provider and the statement from your insurer disagree, it's hard to know why, so most people
          just pay. BillBuddy Health compares the two for you in under a minute, so you can ask the right questions first.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl">How it works</h2>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2">
          {STEPS.map((s, i) => (
            <li key={s.title} className="rounded-2xl bg-card p-5 ring-1 ring-line">
              <div className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-match-soft text-match">{s.icon}</span>
                <p className="font-semibold"><span className="num mr-1.5 text-muted">{i + 1}.</span>{s.title}</p>
              </div>
              <p className="mt-3 text-sm text-muted">{s.text}</p>
            </li>
          ))}
        </ol>
        <p className="mt-5 rounded-2xl bg-match-soft/60 p-5 text-sm">
          <span className="font-semibold">No guesswork.</span> Every item we flag shows the exact numbers behind it, so you
          can see for yourself why it stood out.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl">Disclaimers</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted">
          {DISCLAIMERS.map((d) => <li key={d}>{d}</li>)}
        </ul>
      </section>

      <section className="flex flex-col items-start justify-between gap-4 rounded-2xl bg-card p-6 ring-1 ring-line sm:flex-row sm:items-center">
        <p className="font-display text-xl">Ready to try it?</p>
        <Link to="/analyze" className="inline-flex items-center gap-2 rounded-xl bg-ink px-5 py-2.5 font-medium text-white hover:bg-ink/90">
          Check my bill <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}
