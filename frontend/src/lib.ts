import type { AnalysisResult } from "./types";

export const money = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("en-US", { style: "currency", currency: "USD" });

export const shortDate = (iso: string | null) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

async function readError(res: Response) {
  if ([502, 503, 504].includes(res.status)) {
    return `The server didn't respond (${res.status}). It may be waking up, restarting, or out of memory. Wait a minute and try again; if it keeps happening, check the server logs.`;
  }
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status}). Check that the backend server is running.`;
  }
}

export async function analyzeFiles(bill: File, eob: File): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("bill", bill);
  form.append("eob", eob);
  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchSampleFile(name: string, type: string): Promise<File> {
  const res = await fetch(`/api/samples/${name}`);
  if (!res.ok) throw new Error("Couldn't load the sample documents. Is the backend running?");
  return new File([await res.blob()], name, { type });
}

/** Ask the backend to turn an analysis into a PDF, then save it in the browser. */
export async function downloadReport(result: AnalysisResult): Promise<void> {
  const res = await fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  if (!res.ok) throw new Error(await readError(res));
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "BillBuddy_Report.pdf";
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
