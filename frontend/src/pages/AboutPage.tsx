import { Link } from "react-router-dom";
import { ArrowRight, Bot, Calculator, FileSearch, Link2, MessageSquareQuote, ScanText, User } from "lucide-react";

// ✏️ Edit these with your team's names and roles.
const TEAM = [
  { name: "Team member 1", role: "Backend & document parsing" },
  { name: "Team member 2", role: "Matching & discrepancy rules" },
  { name: "Team member 3", role: "Frontend & design" },
];

const PIPELINE = [
  { icon: <ScanText size={18} />, title: "Read", text: "Text PDFs are read directly (PyMuPDF, pdfplumber). Scans and photos go through Tesseract OCR." },
  { icon: <FileSearch size={18} />, title: "Extract", text: "A rules parser pulls out dates, codes, charges and totals. If the layout is unfamiliar, Gemini reads it instead." },
  { icon: <Link2 size={18} />, title: "Match", text: "Each bill line is scored against each EOB line on code, date, description similarity (RapidFuzz) and amount." },
  { icon: <Calculator size={18} />, title: "Check", text: "Deterministic Python rules compare totals, find duplicates and test whether every line and total adds up." },
  { icon: <MessageSquareQuote size={18} />, title: "Explain", text: "Findings are written in plain English with their evidence and a suggested question for the provider or insurer." },
];

const STACK = [
  "React", "TypeScript", "Vite", "Tailwind CSS", "Recharts", "Python", "FastAPI", "Pydantic",
  "PyMuPDF", "pdfplumber", "Tesseract OCR", "RapidFuzz", "Gemini", "Docker", "Render",
];

export default function AboutPage() {
  return (
    <div className="rise mx-auto max-w-4xl space-y-16 pb-8">
      <section>
        <p className="text-xs font-semibold uppercase tracking-widest text-match">About</p>
        <h1 className="mt-2 font-display text-4xl leading-tight sm:text-5xl">Making medical bills make sense.</h1>
        <p className="mt-5 text-lg text-muted">
          Medical bills and insurance statements are written for billing departments, not patients. When the bill
          from your provider and the Explanation of Benefits from your insurer disagree, most people either pay or give up
          trying to understand why. We built BillBuddy Health so anyone can compare the two in under a minute and walk
          into a billing call with specific, evidence-backed questions.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl">How it works</h2>
        <ol className="mt-6 space-y-3">
          {PIPELINE.map((s, i) => (
            <li key={s.title} className="flex gap-4 rounded-2xl bg-card p-5 ring-1 ring-line">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-match-soft text-match">{s.icon}</span>
              <div>
                <p className="font-semibold"><span className="num mr-2 text-muted">{i + 1}.</span>{s.title}</p>
                <p className="mt-1 text-sm text-muted">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-5 flex gap-3 rounded-2xl bg-eob-soft/60 p-5 text-sm">
          <Bot size={18} className="mt-0.5 shrink-0 text-eob" />
          <p>
            <span className="font-semibold">Where AI fits.</span> Gemini helps read unusual document layouts and writes a short
            summary. It never decides whether something is a discrepancy. That's always arithmetic you can check.
          </p>
        </div>
      </section>

      <section>
        <h2 className="font-display text-2xl">The team</h2>
        <p className="mt-1 text-sm text-muted">Built in 24 hours at HackRU Fall 2026, Rutgers University.</p>
        <ul className="mt-5 grid gap-4 sm:grid-cols-3">
          {TEAM.map((m) => (
            <li key={m.name} className="rounded-2xl bg-card p-5 ring-1 ring-line">
              <span className="grid size-11 place-items-center rounded-full bg-paper text-muted ring-1 ring-line"><User size={20} /></span>
              <p className="mt-3 font-semibold">{m.name}</p>
              <p className="text-sm text-muted">{m.role}</p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl">Built with</h2>
        <ul className="mt-4 flex flex-wrap gap-2">
          {STACK.map((t) => (
            <li key={t} className="rounded-full bg-card px-3 py-1 text-sm ring-1 ring-line">{t}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl">Limitations</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted">
          <li>BillBuddy prepares questions. It doesn't confirm billing errors or give medical, legal or financial advice.</li>
          <li>Bills and EOBs come in thousands of layouts. The rules parser covers common ones; unusual layouts depend on Gemini being available.</li>
          <li>It compares one bill with one EOB for the same claim. Prior balances or charges from other claims can explain some differences.</li>
          <li>Sample documents on this site are fictional. Uploaded files are analyzed and not stored.</li>
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
