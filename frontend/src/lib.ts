import type { AnalysisResult } from "./types";

export const money = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("en-US", { style: "currency", currency: "USD" });

export const shortDate = (iso: string | null) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

async function readError(res: Response) {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status}). Is the backend running on port 8000?`;
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
