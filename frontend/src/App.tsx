import { useState } from "react";
import { RotateCcw } from "lucide-react";
import type { AnalysisResult } from "./types";
import { analyzeFiles } from "./lib";
import UploadPanel from "./components/UploadPanel";
import Analyzing from "./components/Analyzing";
import SummaryHeader from "./components/SummaryHeader";
import MatchBoard from "./components/MatchBoard";
import { ChargeComparison, MoneyFlow } from "./components/Charts";
import Findings from "./components/Findings";
import Glossary from "./components/Glossary";
import ExtractionDetails from "./components/ExtractionDetails";

export default function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState<string[]>([]);

  async function run(bill: File, eob: File) {
    setBusy(true);
    setError(null);
    try {
      // Keep the progress steps visible briefly so the pipeline is legible in a demo.
      const [data] = await Promise.all([analyzeFiles(bill, eob), new Promise((r) => setTimeout(r, 1800))]);
      setResult(data as AnalysisResult);
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function jumpToFinding(ids: string[]) {
    setFocus(ids);
    const f = result?.findings.find((x) => x.related_items.some((id) => ids.includes(id)));
    if (f) document.getElementById(`finding-${f.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line/70 bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <button type="button" onClick={() => { setResult(null); setFocus([]); }} className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-bill text-white">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
            </span>
            <span className="font-display text-xl">BillBuddy <span className="text-match">Health</span></span>
          </button>
          {result && (
            <button type="button" onClick={() => { setResult(null); setFocus([]); }}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm ring-1 ring-line hover:bg-card">
              <RotateCcw size={14} /> New comparison
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {busy ? (
          <Analyzing />
        ) : !result ? (
          <UploadPanel onAnalyze={run} busy={busy} error={error} />
        ) : (
          <div className="space-y-6">
            <SummaryHeader data={result} />
            <MatchBoard data={result} focus={focus} onSelect={jumpToFinding} />
            <div className="grid gap-6 lg:grid-cols-2">
              <ChargeComparison data={result} />
              <MoneyFlow data={result} />
            </div>
            <Findings findings={result.findings} activeIds={focus} onFocus={setFocus} />
            <Glossary terms={result.glossary} />
            <ExtractionDetails bill={result.bill} eob={result.eob} />
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted sm:px-6">
        BillBuddy Health helps you prepare questions; it does not provide medical, legal, or financial advice and
        can't confirm billing errors. Always verify with your provider and insurer. Built at HackRU.
      </footer>
    </div>
  );
}
