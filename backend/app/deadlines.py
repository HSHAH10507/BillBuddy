"""Important dates: when the bill is due, when to call, and the insurance appeal window."""
from __future__ import annotations

from datetime import date, timedelta

from .models import Deadline, ExtractedDocument, Finding

APPEAL_DAYS = 180  # ACA plans: internal appeal within 180 days of the denial notice
APPEAL_SOURCE = "https://www.healthcare.gov/appeal-insurance-company-decision/internal-appeals/"


def _fmt(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def build_deadlines(bill: ExtractedDocument, eob: ExtractedDocument, findings: list[Finding]) -> list[Deadline]:
    out: list[Deadline] = []
    due = date.fromisoformat(bill.due_date) if bill.due_date else None
    review_items = [f for f in findings if f.severity == "review"]

    if due:
        out.append(Deadline(
            id="payment", kind="payment", title="Bill payment due", date=due.isoformat(),
            description=("The date printed on your bill. If you have questions about the charges, contact the billing "
                         "office before this date and ask whether they can pause the bill while it's reviewed."
                         if review_items else "The date printed on your bill."),
        ))

    if review_items:
        # Leave a week before the due date to sort things out; without a due date, aim for two weeks out.
        start = date.fromisoformat(bill.statement_date) if bill.statement_date else date.today()
        call_by = (due - timedelta(days=7)) if due else start + timedelta(days=14)
        if due and call_by < start:
            call_by = start
        asks = {f.ask for f in review_items}
        who = [w for w, keys in (("your provider", {"provider", "either"}), ("your insurer", {"insurer"})) if asks & keys]
        out.append(Deadline(
            id="followup", kind="followup", title=f"Call {' and '.join(who)} about the flagged items", date=call_by.isoformat(),
            description=(f"{len(review_items)} item(s) need a closer look. Calling a week before the due date leaves "
                         "time for a corrected bill. Have your account and claim numbers ready."),
            estimated=True,
        ))

    if eob.processed_date:
        processed = date.fromisoformat(eob.processed_date)
        appeal_by = processed + timedelta(days=APPEAL_DAYS)
        out.append(Deadline(
            id="appeal", kind="appeal", title="Last day to appeal your insurer's decision (estimate)", date=appeal_by.isoformat(),
            description=(f"Most plans give you {APPEAL_DAYS} days (6 months) from the day you received the EOB to file an "
                         f"internal appeal if you disagree with how the claim was processed. This estimate counts from the "
                         f"processed date ({_fmt(processed)}); check your plan documents for your exact deadline."),
            estimated=True, source=APPEAL_SOURCE,
        ))

    out.sort(key=lambda d: d.date)
    return out
