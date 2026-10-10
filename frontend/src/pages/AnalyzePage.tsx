import { useEffect, useState } from "react";
import { Download, Loader2, RotateCcw } from "lucide-react";
import type { AnalysisResult, CodeExplanation } from "../types";
import { analyzeFiles, downloadReport, explainCodes } from "../lib";
import UploadPanel from "../components/UploadPanel";
import Analyzing from "../components/Analyzing";
import SummaryHeader from "../components/SummaryHeader";
import MatchBoard from "../components/MatchBoard";
import { ChargeComparison, MoneyFlow } from "../components/Charts";
import Findings from "../components/Findings";
import Glossary from "../components/Glossary";
import ExtractionDetails from "../components/ExtractionDetails";
import Deadlines from "../components/Deadlines";
import ServicesExplained from "../components/ServicesExplained";

/** The comparison tool: upload a bill + EOB, then see the analysis. (Was the old App.tsx body.) */
export default function AnalyzePage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState<string[]>([]);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // null = still loading; filled in after the results appear so a slow AI call never delays them
  const [explanations, setExplanations] = useState<Record<string, CodeExplanation> | null>(null);

  useEffect(() => {
    if (!result) return;
    setExplanations(null);
    const items = result.pricing.map((p) => ({ code: p.code, description: p.description }));
    if (!items.length) { setExplanations({}); return; }
    let cancelled = false;
    explainCodes(items)
      .then((e) => { if (!cancelled) setExplanations(e); })
      .catch(() => { if (!cancelled) setExplanations({}); });
    return () => { cancelled = true; };
  }, [result]);

  async function saveReport() {
    if (!result) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const code_explanations = Object.fromEntries(Object.entries(explanations ?? {}).map(([k, v]) => [k, v.text]));
      await downloadReport({ ...result, code_explanations });
    } catch (e) {
      setDownloadError((e as Error).message);
    } finally {
      setDownloading(false);
    }
  }

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
      <div className="flex flex-wrap items-center justify-end gap-2">
        {downloadError && <p role="alert" className="mr-auto text-sm text-missing">{downloadError}</p>}
        <button type="button" onClick={reset}
          className="inline-flex items-center gap-1.5 rounded-lg bg-card px-3 py-2 text-sm ring-1 ring-line hover:bg-paper">
          <RotateCcw size={14} /> New comparison
        </button>
        <button type="button" onClick={saveReport} disabled={downloading}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-ink/90 disabled:opacity-60">
          {downloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
          {downloading ? "Preparing PDF…" : "Download PDF report"}
        </button>
      </div>
      <SummaryHeader data={result} />
      <Deadlines deadlines={result.deadlines} />
      <MatchBoard data={result} focus={focus} onSelect={jumpToFinding} />
      <ServicesExplained pricing={result.pricing} pricingSource={result.pricing_source} explanations={explanations} />
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
