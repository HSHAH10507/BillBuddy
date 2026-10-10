import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { AnalysisResult } from "../types";
import { money } from "../lib";

const C = {
  bill: "#0f5f5c", eob: "#3b3f9e", review: "#c27012", missing: "#b4364b",
  discount: "#cfc8b8", paid: "#7d9bb5", owe: "#1c2430", grid: "#e3ddd0", muted: "#5f6b7a",
};

const tooltipStyle = {
  contentStyle: { borderRadius: 12, border: `1px solid ${C.grid}`, fontFamily: "IBM Plex Sans", fontSize: 13 },
  formatter: (v: number) => money(v),
};

export function ChargeComparison({ data }: { data: AnalysisResult }) {
  const bills = new Map(data.bill.line_items.map((i) => [i.id, i]));
  const eobs = new Map(data.eob.line_items.map((i) => [i.id, i]));
  const rows = data.matches.map((m) => {
    const b = m.bill_item_id ? bills.get(m.bill_item_id) : undefined;
    const e = m.eob_item_id ? eobs.get(m.eob_item_id) : undefined;
    const name = (b ?? e)?.code ?? (b ?? e)?.description.slice(0, 10) ?? "?";
    return { name, desc: (b ?? e)?.description ?? "", bill: b?.billed ?? 0, eob: e?.billed ?? 0, status: m.status };
  });
  const flagged = (s: string) => s === "mismatch" || s === "bill_only" || s === "eob_only";

  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
      <h3 className="font-display text-xl">Bill charge vs. what the insurer received</h3>
      <p className="text-sm text-muted">Each pair of bars is one service. Amber bars differ from the EOB or have no match.</p>
      <div className="mt-4 h-72">
        <ResponsiveContainer>
          <BarChart data={rows} barGap={2} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke={C.grid} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fontFamily: "IBM Plex Mono", fill: C.muted }} tickLine={false} axisLine={{ stroke: C.grid }} />
            <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 12, fill: C.muted }} tickLine={false} axisLine={false} width={52} />
            <Tooltip {...tooltipStyle} labelFormatter={(_, p) => (p?.[0]?.payload?.desc as string) ?? ""} cursor={{ fill: "#f6f3ec" }} />
            <Legend wrapperStyle={{ fontSize: 13 }} formatter={(v) => <span style={{ color: "#1c2430" }}>{v}</span>} payload={[
              { value: "Bill charge", type: "square", color: C.bill },
              { value: "EOB billed", type: "square", color: C.eob },
              { value: "Differs / unmatched", type: "square", color: C.review },
            ]} />
            <Bar dataKey="bill" name="Bill charge" radius={[4, 4, 0, 0]}>
              {rows.map((r, i) => <Cell key={i} fill={flagged(r.status) ? C.review : C.bill} />)}
            </Bar>
            <Bar dataKey="eob" name="EOB billed" fill={C.eob} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MoneyFlow({ data }: { data: AnalysisResult }) {
  const bt = data.bill.totals;
  const et = data.eob.totals;
  const rows = [
    { name: "EOB", discount: et.adjustments ?? 0, paid: et.insurance_paid ?? 0, owe: et.patient_responsibility ?? 0 },
    { name: "Bill", discount: bt.adjustments ?? 0, paid: bt.insurance_paid ?? 0, owe: bt.patient_responsibility ?? 0 },
  ];

  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm ring-1 ring-line">
      <h3 className="font-display text-xl">Where the charges went</h3>
      <p className="text-sm text-muted">Both documents split the same visit into discounts, insurance payments, and your share.</p>
      <div className="mt-4 h-48">
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 0 }} barSize={28}>
            <CartesianGrid horizontal={false} stroke={C.grid} />
            <XAxis type="number" tickFormatter={(v) => `$${v}`} tick={{ fontSize: 12, fill: C.muted }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 13, fontWeight: 600, fill: "#1c2430" }} axisLine={false} tickLine={false} width={44} />
            <Tooltip {...tooltipStyle} cursor={{ fill: "#f6f3ec" }} />
            <Legend wrapperStyle={{ fontSize: 13 }} formatter={(v) => <span style={{ color: "#1c2430" }}>{v}</span>} />
            <Bar dataKey="discount" name="Discount / adjustment" stackId="a" fill={C.discount} />
            <Bar dataKey="paid" name="Insurance paid" stackId="a" fill={C.paid} />
            <Bar dataKey="owe" name="Your share" stackId="a" fill={C.owe} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
