import { useEffect, useState } from "react";
import { Check } from "lucide-react";

const STEPS = [
  "Reading text from both documents (PDF text or OCR)",
  "Extracting charges, dates, codes and totals",
  "Matching each bill line to the EOB",
  "Running reconciliation checks",
  "Writing plain-English explanations",
];

export default function Analyzing() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 650);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="rise mx-auto max-w-md rounded-2xl bg-card p-8 shadow-sm ring-1 ring-line" aria-live="polite">
      <p className="font-display text-2xl">Comparing your documents…</p>
      <ol className="mt-6 space-y-3">
        {STEPS.map((s, i) => (
          <li key={s} className={`flex items-center gap-3 text-sm ${i > step ? "text-muted/60" : ""}`}>
            <span className={`grid size-6 place-items-center rounded-full ${i < step ? "bg-match text-white" : "bg-paper ring-1 ring-line"}`}>
              {i < step ? <Check size={14} /> : i === step ? <span className="pulse-dot size-2 rounded-full bg-match" /> : null}
            </span>
            {s}
          </li>
        ))}
      </ol>
    </div>
  );
}
