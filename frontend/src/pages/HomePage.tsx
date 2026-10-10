import { Link } from "react-router-dom";
import {
  ArrowRight, Calculator, CalendarX, Copy, FileText, Hash, Link2, MessageSquareQuote, ReceiptText, Scale,
  SearchCheck, ShieldCheck, Upload,
} from "lucide-react";

const SOURCES = {
  unexpected: {
    label: "Peterson-KFF Health System Tracker, 2020",
    url: "https://www.healthsystemtracker.org/brief/an-examination-of-surprise-medical-bills-and-proposals-to-protect-consumers-from-them-3/",
  },
  denials: {
    label: "KFF, Claims Denials and Appeals in ACA Marketplace Plans in 2024",
    url: "https://www.kff.org/private-insurance/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/",
  },
};

/** Ten receipts, four highlighted: "about four in ten". */
function FourInTen() {
  return (
    <figure className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
      <div className="grid grid-cols-5 gap-3" role="img" aria-label="Four out of ten receipts highlighted">
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i}
            className={`grid aspect-[3/4] place-items-center rounded-lg ${i < 4 ? "bg-review text-white" : "bg-paper text-muted/50 ring-1 ring-line"}`}>
            <ReceiptText size={22} aria-hidden />
          </div>
        ))}
      </div>
      <figcaption className="mt-4 text-sm text-muted">
        About <span className="font-semibold text-review">4 in 10</span> insured adults under 65 got a medical bill they didn't expect.
      </figcaption>
    </figure>
  );
}

function SectionTitle({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-semibold uppercase tracking-widest text-match">{eyebrow}</p>
      <h2 className="mt-2 font-display text-3xl leading-tight sm:text-4xl">{title}</h2>
      {children && <p className="mt-3 text-muted">{children}</p>}
    </div>
  );
}

const STEPS = [
  { icon: <Upload size={20} />, title: "Upload both documents",
    text: "Your provider's bill and your insurer's Explanation of Benefits — PDFs or photos." },
  { icon: <Link2 size={20} />, title: "Every charge gets lined up",
    text: "BillBuddy matches each service across the two documents by code, date, description and amount, even when they word it differently." },
  { icon: <MessageSquareQuote size={20} />, title: "You get evidence and questions",
    text: "Anything that doesn't add up is explained in plain English, with the numbers behind it and a question to ask before you pay." },
];

const CHECKS = [
  { icon: <Scale size={18} />, title: "Bill vs. EOB totals", text: "Is the amount due the same as what your insurer says you owe?" },
  { icon: <Copy size={18} />, title: "Possible duplicates", text: "The same service billed twice on one day." },
  { icon: <ReceiptText size={18} />, title: "Price differences", text: "A charge on the bill that differs from what the insurer received." },
  { icon: <Calculator size={18} />, title: "Math that doesn't add up", text: "Line items vs. totals, and charges minus payments vs. balance." },
  { icon: <CalendarX size={18} />, title: "Date and code mismatches", text: "Services dated or coded differently on the two documents." },
  { icon: <Hash size={18} />, title: "Missing services", text: "Charges on one document with no match on the other." },
];

export default function HomePage() {
  return (
    <div className="space-y-24 pb-8">
      {/* 1. Preface */}
      <section className="rise grid items-center gap-10 pt-4 lg:grid-cols-[1.25fr_1fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">Surprise medical bills are common</p>
          <p className="num mt-4 text-7xl font-medium leading-none text-review sm:text-8xl" aria-hidden>39%</p>
          <h1 className="mt-5 font-display text-3xl leading-snug sm:text-4xl">
            <span className="sr-only">39% </span>of insured adults under 65 received an unexpected medical bill in the
            previous 12 months.
          </h1>
          <p className="mt-4 max-w-xl text-lg text-muted">
            It was a bill they thought insurance would cover, or one that was higher than they anticipated.
          </p>
          <a href={SOURCES.unexpected.url} target="_blank" rel="noreferrer"
            className="mt-4 inline-block text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink">
            Source: {SOURCES.unexpected.label}
          </a>
        </div>
        <FourInTen />
      </section>

      {/* 2. The problem */}
      <section className="space-y-10">
        <SectionTitle eyebrow="The problem" title="Two documents describe the same visit. They don't always agree.">
          After a visit, your provider sends a bill and your insurer sends an Explanation of Benefits (EOB). Comparing them
          line by line is the best way to catch a mistake, but they use different wording, different layouts and terms
          like “allowed amount” and “coinsurance” that most people never learned.
        </SectionTitle>

        <div className="grid items-stretch gap-4 md:grid-cols-[1fr_auto_1fr]">
          <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-bill"><ReceiptText size={15} /> Your bill</p>
            <p className="mt-3 text-sm text-muted">Venipuncture, routine blood draw</p>
            <p className="text-sm text-muted">Venipuncture, routine blood draw</p>
            <p className="mt-4 text-sm text-muted">Amount due</p>
            <p className="num text-3xl text-bill">$299.00</p>
          </div>
          <div className="grid place-items-center">
            <span className="num rounded-full bg-review-soft px-4 py-2 text-sm font-medium text-review ring-1 ring-review/30">$45 gap</span>
          </div>
          <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-eob"><FileText size={15} /> Your EOB</p>
            <p className="mt-3 text-sm text-muted">Collection of venous blood</p>
            <p className="text-sm text-muted/50 italic">— listed once —</p>
            <p className="mt-4 text-sm text-muted">You may owe</p>
            <p className="num text-3xl text-eob">$254.00</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-card p-6 ring-1 ring-line">
            <p className="num text-4xl text-ink">19%</p>
            <p className="mt-2 text-sm text-muted">
              of in-network claims were denied by ACA Marketplace insurers in 2024, so what you're billed and what insurance
              pays can differ a lot.
            </p>
            <a href={SOURCES.denials.url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs text-muted underline underline-offset-4 hover:text-ink">KFF, 2024</a>
          </div>
          <div className="rounded-2xl bg-card p-6 ring-1 ring-line">
            <p className="font-display text-xl">Different words, same service</p>
            <p className="mt-2 text-sm text-muted">“CBC w/ auto diff” on the bill can be “Blood count; complete, automated” on the EOB. Matching them by eye is slow and error-prone.</p>
          </div>
          <div className="rounded-2xl bg-card p-6 ring-1 ring-line">
            <p className="font-display text-xl">The math is hidden</p>
            <p className="mt-2 text-sm text-muted">Charges, adjustments, plan payments, deductibles and coinsurance all have to add up — and nobody shows you the arithmetic.</p>
          </div>
        </div>
      </section>

      {/* 3. Purpose */}
      <section className="space-y-10" id="how-it-works">
        <SectionTitle eyebrow="What BillBuddy does" title="It reads both documents and tells you whether they tell the same story.">
          BillBuddy Health turns two confusing documents into a clear, line-by-line comparison, so
          you can ask the right questions before you pay.
        </SectionTitle>
        <ol className="grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
              <span className="num absolute right-5 top-4 text-sm text-muted">0{i + 1}</span>
              <span className="grid size-10 place-items-center rounded-xl bg-match-soft text-match">{s.icon}</span>
              <p className="mt-4 font-display text-xl">{s.title}</p>
              <p className="mt-2 text-sm text-muted">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* 4. Checks */}
      <section className="space-y-8">
        <SectionTitle eyebrow="What it checks" title="Six things worth a second look" />
        <ul className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
          {CHECKS.map((c) => (
            <li key={c.title} className="flex gap-3">
              <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-card text-review ring-1 ring-line">{c.icon}</span>
              <div>
                <p className="font-semibold">{c.title}</p>
                <p className="text-sm text-muted">{c.text}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* 5. Trust */}
      <section className="grid gap-6 rounded-3xl bg-ink p-8 text-white sm:p-10 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-white/60"><ShieldCheck size={15} /> Evidence, not a black box</p>
          <h2 className="mt-3 font-display text-3xl leading-tight">Every flag comes with the numbers that triggered it.</h2>
          <p className="mt-3 text-white/70">
            Discrepancies are found with plain arithmetic and comparison rules, not an AI guess. AI only helps read
            unusual layouts and summarize the results. BillBuddy never calls something an error. It shows you what
            doesn't line up and what to ask.
          </p>
        </div>
        <ul className="space-y-3 self-center text-sm">
          {["Shows the exact values and document lines behind each finding",
            "Says what it can't determine, so you know what to verify",
            "Files are analyzed and not stored",
          ].map((t) => (
            <li key={t} className="flex gap-3 rounded-xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
              <SearchCheck size={18} className="mt-0.5 shrink-0 text-match-soft" /> {t}
            </li>
          ))}
        </ul>
      </section>

      {/* 6. Call to action */}
      <section className="text-center">
        <h2 className="font-display text-3xl sm:text-4xl">Have a bill and an EOB?</h2>
        <p className="mt-2 text-muted">Compare them in under a minute, or try it with our fictional sample documents.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/analyze" className="inline-flex items-center gap-2 rounded-xl bg-ink px-6 py-3 font-medium text-white shadow-sm hover:bg-ink/90">
            Check my bill <ArrowRight size={16} />
          </Link>
          <Link to="/about" className="rounded-xl bg-card px-6 py-3 font-medium ring-1 ring-line hover:bg-paper">How it works</Link>
        </div>
      </section>

      <section className="border-t border-line pt-6 text-xs text-muted">
        <p className="font-semibold">Sources</p>
        <ul className="mt-2 space-y-1">
          {Object.values(SOURCES).map((s) => (
            <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer" className="underline underline-offset-4 hover:text-ink">{s.label}</a></li>
          ))}
        </ul>
        <p className="mt-2">
          The 39% figure predates the federal No Surprises Act (2022), which limits some surprise out-of-network bills.
          It does not address billing mistakes such as duplicate charges or a bill that disagrees with the EOB.
        </p>
      </section>
    </div>
  );
}
