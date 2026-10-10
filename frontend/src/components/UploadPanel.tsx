import { useRef, useState } from "react";
import { FileText, ReceiptText, ShieldCheck, Sparkles, Upload, X } from "lucide-react";
import { fetchSampleFile } from "../lib";

interface Props {
  onAnalyze: (bill: File, eob: File) => void;
  busy: boolean;
  error: string | null;
}

const ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";

function DropZone({
  label, hint, file, onFile, accent, icon,
}: {
  label: string; hint: string; file: File | null; onFile: (f: File | null) => void;
  accent: "bill" | "eob"; icon: React.ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const ring = accent === "bill" ? "border-bill bg-bill-soft/60" : "border-eob bg-eob-soft/60";

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
      onClick={() => input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      role="button"
      tabIndex={0}
      aria-label={`Upload ${label}`}
      className={`group relative flex min-h-44 cursor-pointer flex-col justify-between rounded-2xl border-2 border-dashed p-5 transition
        ${over || file ? ring : "border-line bg-card hover:border-muted/60"}`}
    >
      <input ref={input} type="file" accept={ACCEPT} className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
      <div className="flex items-start gap-3">
        <div className={`rounded-xl p-2.5 ${accent === "bill" ? "bg-bill text-white" : "bg-eob text-white"}`}>{icon}</div>
        <div>
          <p className="font-display text-lg leading-tight">{label}</p>
          <p className="text-sm text-muted">{hint}</p>
        </div>
      </div>
      {file ? (
        <div className="mt-4 flex items-center justify-between gap-2 rounded-xl bg-card px-3 py-2 shadow-sm ring-1 ring-line">
          <span className="flex min-w-0 items-center gap-2 text-sm">
            <FileText size={16} className="shrink-0 text-muted" />
            <span className="truncate">{file.name}</span>
          </span>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onFile(null); if (input.current) input.current.value = ""; }}
            className="rounded-md p-1 text-muted hover:bg-paper hover:text-ink"
            aria-label={`Remove ${file.name}`}
          ><X size={16} /></button>
        </div>
      ) : (
        <p className="mt-4 flex items-center gap-2 text-sm text-muted">
          <Upload size={16} /> Drop a PDF or photo, or click to browse
        </p>
      )}
    </div>
  );
}

export default function UploadPanel({ onAnalyze, busy, error }: Props) {
  const [bill, setBill] = useState<File | null>(null);
  const [eob, setEob] = useState<File | null>(null);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);

  async function loadSamples(scanned = false) {
    setLoadingSamples(true);
    setSampleError(null);
    try {
      const [b, e] = await Promise.all([
        scanned ? fetchSampleFile("sample_bill_photo.png", "image/png") : fetchSampleFile("sample_bill.pdf", "application/pdf"),
        fetchSampleFile("sample_eob.pdf", "application/pdf"),
      ]);
      setBill(b);
      setEob(e);
    } catch (err) {
      setSampleError((err as Error).message);
    } finally {
      setLoadingSamples(false);
    }
  }

  return (
    <section className="rise mx-auto max-w-4xl">
      <div className="mb-8 text-center">
        <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-card px-3 py-1 text-xs font-medium tracking-wide text-match ring-1 ring-line">
          <ShieldCheck size={14} /> Every finding shows its evidence
        </p>
        <h1 className="font-display text-4xl leading-tight sm:text-5xl">
          Is your medical bill <span className="italic text-match">telling the same story</span> as your insurer?
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-muted">
          Upload the bill from your provider and the Explanation of Benefits from your insurer. BillBuddy lines up
          every charge, checks the math, and explains anything a human should look at before you pay.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <DropZone label="Medical bill" hint="The statement from your doctor or hospital" file={bill} onFile={setBill}
          accent="bill" icon={<ReceiptText size={20} />} />
        <DropZone label="Explanation of Benefits" hint="The EOB from your insurance company" file={eob} onFile={setEob}
          accent="eob" icon={<FileText size={20} />} />
      </div>

      {(error || sampleError) && (
        <p role="alert" className="mt-4 rounded-xl bg-missing-soft px-4 py-3 text-sm text-missing">{error || sampleError}</p>
      )}

      <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          <button type="button" onClick={() => loadSamples(false)} disabled={loadingSamples}
            className="inline-flex items-center gap-1.5 font-medium text-match underline-offset-4 hover:underline disabled:opacity-50">
            <Sparkles size={15} /> {loadingSamples ? "Loading…" : "Load sample documents"}
          </button>
          <button type="button" onClick={() => loadSamples(true)} disabled={loadingSamples}
            className="text-muted underline-offset-4 hover:text-ink hover:underline disabled:opacity-50">
            or a photographed bill (OCR)
          </button>
        </div>
        <button
          type="button"
          disabled={!bill || !eob || busy}
          onClick={() => bill && eob && onAnalyze(bill, eob)}
          className="w-full rounded-xl bg-ink px-6 py-3 font-medium text-white shadow-sm transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
        >
          {busy ? "Analyzing…" : "Compare documents"}
        </button>
      </div>
      <p className="mt-6 text-center text-xs text-muted">
        Sample documents are fictional. Files are processed by your local BillBuddy server and are not stored.
      </p>
    </section>
  );
}
