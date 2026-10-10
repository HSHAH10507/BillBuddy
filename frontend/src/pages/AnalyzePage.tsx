import { useState } from "react";
import { RotateCcw } from "lucide-react";
import type { AnalysisResult } from "../types";
import { analyzeFiles } from "../lib";
import UploadPanel from "../components/UploadPanel";
import Analyzing from "../components/Analyzing";
import SummaryHeader from "../components/SummaryHeader";
import MatchBoard from "../components/MatchBoard";
import { ChargeComparison, MoneyFlow } from "../components/Charts";
import Findings from "../components/Findings";
import Glossary from "../components/Glossary";
import ExtractionDetails from "../components/ExtractionDetails";

/** The comparison tool: upload a bill + EOB, then see the analysis. (Was the old App.tsx body.) */
export default function AnalyzePage() {
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

  function reset() {
    setResult(null);
    setFocus([]);
    window.scrollTo({ top: 0 });
  }

  function jumpToFinding(ids: string[]) {
    setFocus(ids);
    const f = result?.findings.find((x) => x.related_items.some((id) => ids.includes(id)));
    if (f) document.getElementById(`finding-${f.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (busy) return <Analyzing />;
  if (!result) return <UploadPanel onAnalyze={run} busy={busy} error={error} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button type="button" onClick={reset}
          className="inline-flex items-center gap-1.5 rounded-lg bg-card px-3 py-1.5 text-sm ring-1 ring-line hover:bg-paper">
          <RotateCcw size={14} /> New comparison
        </button>
      </div>
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
  );
}
