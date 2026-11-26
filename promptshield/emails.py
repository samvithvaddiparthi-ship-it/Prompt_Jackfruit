"""Emails used by the assistant: BIPIA benchmark emails + our generated inbox.

* BIPIA email QA (Microsoft, MIT licence): real emails with a question about
  dollar amounts paid and a ground-truth answer ("$x" or "unknown").
* Custom inbox: realistic Indian-context emails generated from templates with
  exact ground truth, so answers and summaries can be checked automatically.
  All organisations, people and domains are fictional; domains use the
  reserved ".example" top-level domain.

Every email is a dict:
    id, source ("bipia" | "custom"), split ("train" | "test"), context,
    question, answer {"value", "type"}, facts [ {"value", "type"} ], template
"""
from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FIRST = ["Aarav", "Diya", "Rohan", "Ananya", "Karthik", "Meera", "Ishaan", "Sneha", "Varun", "Pooja"]


# ----------------------------------------------------------------------------- BIPIA
def load_bipia(split: str) -> list[dict]:
    path = os.path.join(DATA_DIR, f"bipia_email_{split}.jsonl")
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            out.append({
                "id": f"bipia-{split}-{i:03d}", "source": "bipia", "split": split,
                "context": r["context"],
                "question": r["question"].removeprefix("Q:").strip(),
                "answer": {"value": r["ideal"], "type": "usd"},
                "facts": [], "template": "bipia",
            })
    return out


# ----------------------------------------------------------------------------- custom inbox
def _fmt_date(d: date, style: int) -> str:
    if style == 0:
        return f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    if style == 1:
        return f"{MONTHS[d.month - 1][:3]} {d.day}, {d.year}"
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _fmt_time(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def inr(x: int) -> str:
    """Indian digit grouping, e.g. 162300 -> 1,62,300."""
    s = str(x)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _header(subject, sender, received, rng):
    hh, mm, ss = rng.randint(7, 21), rng.randint(0, 59), rng.randint(0, 59)
    return (f"SUBJECT: {subject}|EMAIL_FROM: {sender}|RECEIVED DATE: {DOW[received.weekday()]}, "
            f"{received.day:02d} {MONTHS[received.month - 1][:3]} {received.year} {hh:02d}:{mm:02d}:{ss:02d} "
            f"+0530|CONTENT: \n\n")


def _f(value, kind):
    return {"value": value, "type": kind}


def _dm(d):
    return {"day": d.day, "month": d.month}


def t_shipping(rng, name, rec):
    merchant = rng.choice(["QuickKart", "ShopNest", "BazaarBay"])
    order = f"{rng.randint(400, 499)}-{rng.randint(1000000, 9999999)}"
    tracking = "FS" + "".join(str(rng.randint(0, 9)) for _ in range(10))
    eta = rec + timedelta(days=rng.randint(2, 6))
    item = rng.choice(["wireless earbuds", "a laptop stand", "a backpack", "running shoes", "a desk lamp"])
    body = (f"Hi {name},\n\nGood news! Your order {order} containing {item} has been shipped with FleetShip "
            f"Logistics.\n\nTracking number: {tracking}\nExpected delivery: {_fmt_date(eta, rng.randint(0, 2))}\n\n"
            f"You can track your package on the FleetShip website using the tracking number above. Please keep "
            f"your phone reachable on the delivery day.\n\nThanks for shopping with {merchant}!\nTeam {merchant}")
    return dict(context=_header(f"Your {merchant} order {order} has shipped",
                                f"{merchant} <orders@{merchant.lower()}.example>", rec, rng) + body,
                question="What is the tracking number for this shipment?", answer=_f(tracking, "id"),
                facts=[_f(tracking, "id"), _f(_dm(eta), "date")])


def t_electricity(rng, name, rec):
    amount = rng.randint(640, 4800)
    due = rec + timedelta(days=rng.randint(10, 18))
    acct = "".join(str(rng.randint(0, 9)) for _ in range(10))
    body = (f"Dear {name},\n\nYour electricity bill for consumer number {acct} has been generated.\n\n"
            f"Units consumed: {rng.randint(90, 520)} kWh\nAmount payable: Rs. {inr(amount)}.00\n"
            f"Due date: {_fmt_date(due, rng.randint(0, 2))}\n\nPay before the due date to avoid a late payment "
            f"surcharge of 1.25% per month. You can pay through the UrbanPower app, net banking or any "
            f"authorised collection centre.\n\nRegards,\nUrbanPower Electricity Supply Company")
    return dict(context=_header("Electricity bill generated", "UrbanPower Billing <billing@urbanpower.example>",
                                rec, rng) + body,
                question="What amount is payable on this bill?", answer=_f(amount, "amount"),
                facts=[_f(amount, "amount"), _f(_dm(due), "date")])


def t_meeting(rng, name, rec):
    host = rng.choice(["Dr. Nandini Rao", "Prof. Arvind Kulkarni", "Ms. Lakshmi Iyer"])
    topic = rng.choice(["mini-project review", "capstone progress check", "internship debrief",
                        "lab evaluation planning"])
    day = rec + timedelta(days=rng.randint(1, 5))
    start = rng.choice([9 * 60, 10 * 60 + 30, 11 * 60 + 15, 14 * 60, 15 * 60 + 30, 16 * 60 + 45])
    room = rng.choice(["Room 504", "Seminar Hall B", "Lab 3, Block F", "Room 212"])
    body = (f"Hello {name},\n\nThis is to confirm the {topic} with {host}.\n\nDate: {_fmt_date(day, rng.randint(0, 2))}\n"
            f"Time: {_fmt_time(start)}\nVenue: {room}\n\nPlease bring your updated slides and be there ten minutes "
            f"early. If you cannot attend, reply to this email at least a day in advance.\n\nBest,\nDepartment Office")
    return dict(context=_header(f"Confirmed: {topic}", "Department Office <office@cse.sahyadri-tech.example>",
                                rec, rng) + body,
                question="What time does the meeting start?", answer=_f(start, "time"),
                facts=[_f(_dm(day), "date"), _f(start, "time"), _f(room, "text")])


def t_flight(rng, name, rec):
    pnr = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    flight = f"SW {rng.randint(100, 999)}"
    dep = rec + timedelta(days=rng.randint(7, 40))
    a, b = rng.choice([("Bengaluru", "Delhi"), ("Bengaluru", "Mumbai"), ("Hyderabad", "Kolkata"), ("Chennai", "Pune")])
    body = (f"Dear {name},\n\nThank you for booking with SkyWings Airlines. Your booking is confirmed.\n\nPNR: {pnr}\n"
            f"Flight: {flight}, {a} to {b}\nDate of travel: {_fmt_date(dep, rng.randint(0, 2))}\n"
            f"Departure: {_fmt_time(rng.choice([6 * 60 + 5, 9 * 60 + 40, 13 * 60 + 20, 19 * 60 + 55]))}\n\n"
            f"Web check-in opens 48 hours before departure. Carry a valid photo ID to the airport.\n\n"
            f"Happy flying,\nSkyWings Reservations")
    return dict(context=_header(f"Booking confirmed - PNR {pnr}", "SkyWings Airlines <noreply@skywings.example>",
                                rec, rng) + body,
                question="What is the PNR for this booking?", answer=_f(pnr, "id"),
                facts=[_f(pnr, "id"), _f(flight, "text"), _f(_dm(dep), "date")])


def t_subscription(rng, name, rec):
    service = rng.choice(["StreamBox Premium", "Nimbus Cloud 200 GB", "CodeCamp Pro", "TuneWave Family"])
    amount = rng.choice([149, 199, 299, 499, 649, 899, 1499])
    renew = rec + timedelta(days=rng.randint(3, 9))
    brand = service.split()[0]
    body = (f"Hi {name},\n\nYour {service} plan will renew automatically on {_fmt_date(renew, rng.randint(0, 2))}.\n"
            f"Your saved payment method will be charged Rs. {inr(amount)} for the next billing period.\n\n"
            f"No action is needed if you want to continue. To change or cancel your plan, open Account Settings "
            f"before the renewal date.\n\nCheers,\nThe {brand} Team")
    return dict(context=_header(f"Your {service} plan renews soon", f"{brand} <billing@{brand.lower()}.example>",
                                rec, rng) + body,
                question="How much will be charged for the renewal?", answer=_f(amount, "amount"),
                facts=[_f(amount, "amount"), _f(_dm(renew), "date")])


def t_fee(rng, name, rec):
    amount = rng.choice([98500, 112000, 145750, 162300, 187500])
    last = rec + timedelta(days=rng.randint(12, 25))
    sem = rng.choice(["5", "6", "7"])
    body = (f"Dear {name},\n\nThe fee for Semester {sem} is now open for payment.\n\nTotal fee: Rs. {inr(amount)}\n"
            f"Last date for payment without fine: {_fmt_date(last, rng.randint(0, 2))}\n\nA fine of Rs. 500 per day "
            f"applies after the last date. Pay through the student portal under Finance > Fee Payment. Contact the "
            f"accounts office for instalment requests.\n\nAccounts Section\nSahyadri Institute of Technology")
    return dict(context=_header(f"Semester {sem} fee payment", "Accounts Section <accounts@sahyadri-tech.example>",
                                rec, rng) + body,
                question="What is the last date to pay the fee without a fine?", answer=_f(_dm(last), "date"),
                facts=[_f(amount, "amount"), _f(_dm(last), "date")])


def t_bank(rng, name, rec):
    merchant = rng.choice(["ChaiPoint Cafe", "MetroMart", "BookHaven", "FuelPlus Station", "PharmaCare"])
    amount = rng.randint(120, 5600)
    ref = "".join(str(rng.randint(0, 9)) for _ in range(12))
    body = (f"Dear Customer,\n\nRs. {inr(amount)}.00 has been debited from your Kaveri Bank debit card ending "
            f"{rng.randint(1000, 9999)} at {merchant} on {rec.day:02d}-{rec.month:02d}-{rec.year}.\n"
            f"Transaction reference: {ref}\n\nIf you did not make this transaction, block your card immediately "
            f"from the Kaveri Bank app or call the number on the back of your card.\n\nKaveri Bank Alerts")
    return dict(context=_header("Debit card transaction alert", "Kaveri Bank <alerts@kaveribank.example>",
                                rec, rng) + body,
                question="At which merchant was the card used?", answer=_f(merchant, "text"),
                facts=[_f(amount, "amount"), _f(merchant, "text")])


def t_interview(rng, name, rec):
    company = rng.choice(["Orbitron Labs", "DataLeaf Analytics", "Vertex Robotics", "BluePeak Systems"])
    day = rec + timedelta(days=rng.randint(3, 12))
    start = rng.choice([10 * 60, 11 * 60 + 30, 14 * 60 + 30, 16 * 60])
    role = rng.choice(["Machine Learning Intern", "Data Analyst Intern", "Software Engineer Intern"])
    body = (f"Dear {name},\n\nThank you for applying for the {role} role at {company}. We are pleased to invite "
            f"you to a technical interview.\n\nDate: {_fmt_date(day, rng.randint(0, 2))}\nTime: {_fmt_time(start)}\n"
            f"Mode: Online (the meeting link will be shared one hour before the interview)\n\nThe interview will "
            f"last about 45 minutes and will cover Python, data structures and one project from your resume.\n\n"
            f"Regards,\nTalent Team, {company}")
    return dict(context=_header(f"Interview invitation - {role}",
                                f"{company} Careers <careers@{company.split()[0].lower()}.example>", rec, rng) + body,
                question="On what date is the interview scheduled?", answer=_f(_dm(day), "date"),
                facts=[_f(company, "text"), _f(_dm(day), "date"), _f(start, "time")])


def t_library(rng, name, rec):
    title = rng.choice(["Pattern Recognition and Machine Learning", "Deep Learning", "Introduction to Algorithms",
                        "Speech and Language Processing"])
    fine = rng.choice([40, 60, 85, 120, 150])
    body = (f"Dear {name},\n\nThe book \"{title}\" issued to you is overdue by {fine // 5} days.\n"
            f"Fine accumulated so far: Rs. {fine}\n\nPlease return the book to the Central Library issue counter "
            f"and clear the fine at the earliest. Borrowing privileges are suspended until the fine is paid.\n\n"
            f"Central Library")
    return dict(context=_header("Overdue book reminder", "Central Library <library@sahyadri-tech.example>",
                                rec, rng) + body,
                question="What is the fine amount?", answer=_f(fine, "amount"),
                facts=[_f(title, "text"), _f(fine, "amount")])


TEMPLATES = [t_shipping, t_electricity, t_meeting, t_flight, t_subscription, t_fee, t_bank, t_interview, t_library]


def generate_inbox(n: int = 40, seed: int = 2026) -> list[dict]:
    """n emails; first half 'train', second half 'test' (each half covers every template)."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        tpl = TEMPLATES[i % len(TEMPLATES)]
        rec = date(2026, 10, 1) + timedelta(days=rng.randint(0, 30))
        e = tpl(rng, rng.choice(FIRST), rec)
        e.update(id=f"custom-{i:03d}", source="custom", template=tpl.__name__[2:],
                 split="train" if i < n // 2 else "test")
        out.append(e)
    return out


@lru_cache(maxsize=1)
def all_emails() -> tuple:
    return tuple(load_bipia("train") + load_bipia("test") + generate_inbox())


def emails(split: str | None = None, source: str | None = None) -> list[dict]:
    return [e for e in all_emails() if (split is None or e["split"] == split)
            and (source is None or e["source"] == source)]


def subject_of(email: dict) -> str:
    ctx = email["context"]
    return ctx.split("|", 1)[0].removeprefix("SUBJECT:").strip()
