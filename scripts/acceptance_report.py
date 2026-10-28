"""Run the suite and write docs/ACCEPTANCE_STATUS.md (DECISIONS.md D-S02).

    uv run python -m scripts.acceptance_report

Each acceptance case maps to the tests that evidence it and an honest status category. A
mapped case is reported with its category only if every mapped test passed in this run;
otherwise it is reported `failed`. Unmapped cases carry their declared status and reason.
"""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

D, S, B = "passed_domain", "passed_simulator", "passed_browser"
DEFER, MANUAL, PROVIDER = "deferred_not_in_scope", "manual_pending", "provider_pending"

# id: (scenario, status if tests pass, [test name substrings], limitation)
CASES: dict[str, tuple[str, str, list[str], str]] = {
    "T01": ("Exact item and verified mapping", D, ["test_t01_"], ""),
    "T02": ("2 litres vs two 2-litre bottles", D, ["test_t02_"], ""),
    "T03": (
        "Low-confidence shelf-photo match",
        D,
        ["test_t03_"],
        "Fabricated extraction only; real camera/OCR accuracy unproven.",
    ),
    "T04": ("Locked item unavailable", D, ["test_t04_"], ""),
    "T05": ("Must-have fails in allow-partial basket", S, ["test_t05_"], ""),
    "T06": (
        "Optional item removed under permission",
        S,
        ["test_t06_", "test_immediate_permitted_omission"],
        "",
    ),
    "T07": ("Stock observed but no hold", S, ["test_t07_"], ""),
    "T08": ("Reservation expires during 3DS", S, ["test_t08_"], ""),
    "T09": ("Immediate payment after hold expiry", S, ["test_t09_"], ""),
    "T10": ("Merchant loses reserved stock", S, ["test_t10_"], ""),
    "T11": ("Delivery threshold changes split", D, ["test_t11_"], ""),
    "T12": ("Ineligible loyalty promotion", D, ["test_t12_"], ""),
    "T13": ("VAT-inclusive price, no second VAT", D, ["vat_inclusive_t13"], ""),
    "T14": ("Larger pack cheaper per unit", D, ["test_t14_"], ""),
    "T15": ("Solver timeout with incumbent", D, ["test_t15_"], ""),
    "T16": ("Cheapest misses deadline", D, ["test_t16_"], ""),
    "T17": ("Fastest-complete uses final leg", D, ["test_t17_"], ""),
    "T18": ("Approved conditions altered", D, ["test_t18_"], ""),
    "T19": ("Address changes behind an id", D, ["test_t19_"], ""),
    "T20": ("Replayed approval assertion", D, ["test_t20_"], ""),
    "T21": ("Wrong origin/account/credential", D, ["test_t21_"], ""),
    "T22": (
        "PIN-capable device, no Face ID",
        B,
        ["test_t22_", "test_approval_page_with_virtual_passkey"],
        "Virtual authenticator only; a physical PIN-only device is manual_pending.",
    ),
    "T23": (
        "Recycled phone number recovery",
        D,
        ["test_t23_"],
        "Negative boundary only: no phone-based recovery exists. Full recovery journey not built.",
    ),
    "T24": ("Parallel orders from one approval", D, ["test_t24_"], ""),
    "T25": ("Same key, changed payload", D, ["test_t25_"], ""),
    "T26": ("Provider accepted, response lost", S, ["test_t26_"], ""),
    "T27": ("Unknown beyond provider horizon", S, ["test_t27_"], ""),
    "T28": ("Duplicate/out-of-order webhook", S, ["test_t28_"], ""),
    "T29": ("Invalid webhook signature", D, ["test_t29_"], ""),
    "T30": ("Callback vs lookup conflict", S, ["test_t30_"], ""),
    "T31": (
        "Two destinations, single-destination product",
        S,
        ["test_t31_"],
        "Simulated profiles; real provider capabilities are provider_pending (D02).",
    ),
    "T32": (
        "Retailer-specific refund on proportional split",
        S,
        ["test_t32_"],
        "Simulated allocation; real provider behaviour provider_pending.",
    ),
    "T33": ("Partial refunds race", S, ["test_t33_"], ""),
    "T34": ("Refund timeout then user retry", S, ["test_t34_"], ""),
    "T35": (
        "Refund and chargeback overlap",
        S,
        ["test_t35_"],
        "Detection and hold only; dispute evidence workflow is operational.",
    ),
    "T36": ("Merchant payout fails", S, ["test_t53_t36_t54_settlement_import"], ""),
    "T37": ("Full basket fails before capture", S, ["test_t37_"], ""),
    "T38": ("One leg fails after another commits", S, ["test_t38_"], ""),
    "T39": ("Cancellation races capture", S, ["test_t39_", "test_cancel_during_checkout"], ""),
    "T40": ("Courier booking times out", S, ["test_t40_"], ""),
    "T41": (
        "Consolidated pickup, second store late",
        DEFER,
        [],
        "Consolidation is disabled (D-S03.1); every leg is delivered separately.",
    ),
    "T42": ("Delivery to unapproved address", S, ["test_t42_"], ""),
    "T43": (
        "Missing/damaged package",
        S,
        ["test_t43_"],
        "Targeted refund only; evidence handling and liability are operational.",
    ),
    "T44": (
        "Product recall",
        D,
        ["test_t44_"],
        "Identification of affected orders only; response workflow manual_pending.",
    ),
    "T45": ("Malicious merchant description", D, ["test_t45_"], ""),
    "T46": (
        "Malicious URL in product/media",
        D,
        ["test_t46_"],
        "No fetch capability exists in app code; production egress policy is an "
        "environment requirement.",
    ),
    "T47": ("Model claims payment without evidence", D, ["test_t47_"], ""),
    "T48": (
        "Model poisons stored preference",
        D,
        ["test_t48_"],
        "Fixture agent; robustness of a real model unproven.",
    ),
    "T49": ("Another account's UUID", D, ["test_t49_"], ""),
    "T50": ("Restore after outbox commit", S, ["test_t50_"], ""),
    "T51": ("Restore after provider accepted", S, ["test_t51_"], ""),
    "T52": ("Unbalanced ledger posting", D, ["test_t52_", "rejects_unbalanced"], ""),
    "T53": ("Settlement report imported twice", S, ["test_t53_t36_t54_settlement_import"], ""),
    "T54": ("Unexplained discrepancy", S, ["test_t54_"], ""),
    "T55": (
        "WhatsApp unavailable",
        DEFER,
        [],
        "No WhatsApp channel in this sprint; web status/receipts are the only channel.",
    ),
    "T56": (
        "ID/card details in chat",
        DEFER,
        ["test_redaction_"],
        "No chat channel. Log/audit redaction is tested; the chat handling path is not built.",
    ),
    "T57": (
        "Non-converting sessions cost",
        DEFER,
        [],
        "Cost instrumentation (cost_events) not built this sprint.",
    ),
    "T58": (
        "Low reserve or support overload",
        D,
        ["test_t58_", "test_kill_switch_does_not_block"],
        "Kill switch limits new exposure; reserve and support-load measurement not built.",
    ),
    "T59": (
        "Language-specific extraction fails",
        DEFER,
        ["test_t02_ambiguous"],
        "No language model. Ambiguous items already block quoting until clarified.",
    ),
    "T60": ("List exceeds ambient pilot coverage", D, ["test_t60_"], ""),
    "W01": ("Duplicate confirmed top-up", S, ["test_w01_"], ""),
    "W02": ("Top-up pending/failed/unverified", S, ["test_w02_"], ""),
    "W03": ("Wrong currency/destination/reference", S, ["test_w03_"], ""),
    "W04": ("Concurrent allocation", D, ["test_w04_"], ""),
    "W05": (
        "Concurrent spend on one envelope (A3)",
        D,
        ["test_w05a_", "test_w05b_", "test_w05c_"],
        "",
    ),
    "W06": ("Funds without grant/approval", D, ["test_w06_"], ""),
    "W07": ("Grant without funds", D, ["test_w07_"], ""),
    "W08": ("Agent broadens scope / redirects", D, ["test_w08_"], ""),
    "W09": ("Revoked between request and commitment", S, ["test_w09_"], ""),
    "W10": ("Cancellation after uncertain merchant action", S, ["test_w10_"], ""),
    "W11": ("Reservation release delivered twice", D, ["test_w11_"], ""),
    "W12": ("Partial refunds race or repeat", D, ["test_w12_"], ""),
    "W13": ("Confirmed top-up later reversed", S, ["test_w13_"], ""),
    "W14": ("Redemption races purchase", D, ["test_w05b_w14_"], ""),
    "W15": ("Small orders evade per-order cap", D, ["test_w15_"], ""),
    "W16": ("Wallet purchase, no external debit", S, ["test_w16_"], ""),
    "W17": ("Operating vs customer funds", D, ["test_w17_"], ""),
    "W18": ("Refund near period boundary", D, ["test_w18_"], ""),
    "W19": ("Crash after external result", S, ["test_w19_"], ""),
    "W20": ("Synthetic DB under live config", D, ["test_w20_"], ""),
}


def run_suite() -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "junit.xml"
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:warnings", f"--junitxml={xml}"],
            check=False,
        )
        results = {}
        for case in ET.parse(xml).getroot().iter("testcase"):
            outcome = "passed"
            for child in case:
                if child.tag in ("failure", "error"):
                    outcome = "failed"
                elif child.tag == "skipped":
                    outcome = "skipped"
            results[f"{case.get('classname')}::{case.get('name')}"] = outcome
        return results


def main() -> None:
    results = run_suite()
    rows, counts = [], {}
    for case_id, (scenario, status, needles, limitation) in CASES.items():
        matched = {
            name: outcome
            for name, outcome in results.items()
            if any(n in name.rsplit("::", 1)[1] for n in needles)
        }
        if needles and not matched:
            final = "failed"
            limitation = (limitation + " " if limitation else "") + "No mapped test found."
        elif matched and any(o != "passed" for o in matched.values()):
            final = "failed" if any(o == "failed" for o in matched.values()) else "skipped"
        else:
            final = status
        counts[final] = counts.get(final, 0) + 1
        tests = ", ".join(sorted({n.rsplit("::", 1)[1].split("[")[0] for n in matched})) or "—"
        rows.append(f"| {case_id} | {scenario} | `{final}` | {tests} | {limitation} |")
    total = len(results)
    passed = sum(1 for o in results.values() if o == "passed")
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    doc = "\n".join(
        [
            "# Acceptance status",
            "",
            f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `scripts/acceptance_report.py`. "
            f"Suite: {passed}/{total} tests passed.",
            "",
            "Statuses follow DECISIONS.md D-S02. `passed_domain` and `passed_simulator` are "
            "evidence about this code against fixtures and simulators; they are **not** evidence "
            "about any real provider, merchant, courier, device or operation. SIMULATED — NOT "
            "REAL MONEY.",
            "",
            f"Summary: {summary}.",
            "",
            "| ID | Scenario | Status | Evidence (tests) | Limitations |",
            "|---|---|---|---|---|",
            *rows,
            "",
        ]
    )
    Path("docs/ACCEPTANCE_STATUS.md").write_text(doc)
    print(f"wrote docs/ACCEPTANCE_STATUS.md — {summary}")
    sys.exit(0 if "failed" not in counts else 1)


if __name__ == "__main__":
    main()
