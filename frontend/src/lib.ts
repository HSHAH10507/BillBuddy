import type { AnalysisResult, CodeExplanation, Deadline } from "./types";

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

/** Plain-English explanations for billing codes (Gemini on the server, with built-in fallback text). */
export async function explainCodes(items: { code: string; description: string }[]): Promise<Record<string, CodeExplanation>> {
  const res = await fetch("/api/explain-codes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()).explanations;
}

/** Whole days from today until an ISO date (negative if it has passed). */
export function daysUntil(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const today = new Date();
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((Date.UTC(y, m - 1, d) - start) / 86_400_000);
}

/** Build an .ics calendar file (all-day events with a reminder 2 days before) and download it. */
export function downloadCalendar(deadlines: Deadline[], filename = "BillBuddy_Deadlines.ics"): void {
  const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/;/g, "\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
  const ymd = (iso: string) => iso.replace(/-/g, "");
  const nextDay = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    const t = new Date(Date.UTC(y, m - 1, d + 1));
    return t.toISOString().slice(0, 10).replace(/-/g, "");
  };
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const events = deadlines.map((d) => [
    "BEGIN:VEVENT",
    `UID:${d.id}-${d.date}@billbuddy.health`,
    `DTSTAMP:${stamp}`,
    `DTSTART;VALUE=DATE:${ymd(d.date)}`,
    `DTEND;VALUE=DATE:${nextDay(d.date)}`,
    `SUMMARY:${esc(`BillBuddy: ${d.title}`)}`,
    `DESCRIPTION:${esc(d.description + (d.source ? `\n${d.source}` : ""))}`,
    "BEGIN:VALARM", "TRIGGER:-P2D", "ACTION:DISPLAY", `DESCRIPTION:${esc(d.title)}`, "END:VALARM",
    "END:VEVENT",
  ].join("\r\n"));
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BillBuddy Health//EN", "CALSCALE:GREGORIAN",
    ...events, "END:VCALENDAR"].join("\r\n");
  const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
