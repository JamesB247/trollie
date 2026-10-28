"""Server-rendered pages: the trusted approval page, the wallet view, the merchant harness.

The approval page is rendered from the server's immutable record only; nothing displayed
comes from the client or the agent (blueprint §13.1; PRD UX "authoritative basket").
"""

import html
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import COOKIE, token_from, verify
from app.api.deps import AppContext, ctx, db, dev_only
from app.clock import PRESENTATION_TZ
from app.errors import TrollieError
from app.orders.models import DeliveryJob, Order, OrderLeg
from app.quotes.service import owned_quote
from app.wallet.models import Grant

router = APIRouter()

STYLE = """
:root{--bg:#f7f7f5;--fg:#1d1d1b;--muted:#5f5f5a;--line:#dcdcd6;--accent:#1f6f4a;--warn:#8a4b00}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;
background:var(--bg);color:var(--fg)}main{max-width:560px;margin:0 auto;padding:16px}
.banner{background:#fff3d6;border:1px solid #e8c77a;color:var(--warn);padding:8px 12px;
border-radius:8px;font-weight:600;margin-bottom:12px}h1{font-size:1.3rem;margin:.2rem 0 1rem}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px;margin:10px 0}
.row{display:flex;justify-content:space-between;gap:12px}.muted{color:var(--muted);font-size:.9rem}
.total{font-size:1.2rem;font-weight:700}button{width:100%;padding:14px;margin-top:10px;
font-size:1rem;border:0;border-radius:10px;background:var(--accent);color:#fff}
button.secondary{background:#fff;color:var(--accent);border:1px solid var(--accent)}
ul{padding-left:1.1rem;margin:.3rem 0}#msg{margin-top:10px;font-weight:600}
"""

SCRIPT = """
const b64u = {
  dec: s => Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/') + '==='.slice((s.length+3)%4)), c => c.charCodeAt(0)),
  enc: b => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'')
};
const msg = t => { document.getElementById('msg').textContent = t; };
async function post(url, body, headers) {
  const r = await fetch(url, {method:'POST', credentials:'same-origin',
    headers: Object.assign({'content-type':'application/json'}, headers||{}),
    body: JSON.stringify(body||{})});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((data.code||r.status) + ': ' + (data.message||JSON.stringify(data)));
  return data;
}
async function registerPasskey() {
  try {
    const {challenge_id, options} = await post('/v1/passkeys/registration-options');
    const o = JSON.parse(options);
    o.challenge = b64u.dec(o.challenge); o.user.id = b64u.dec(o.user.id);
    o.excludeCredentials = (o.excludeCredentials||[]).map(c => ({...c, id: b64u.dec(c.id)}));
    const cred = await navigator.credentials.create({publicKey: o});
    await post('/v1/passkeys', {challenge_id, credential: {id: cred.id, rawId: b64u.enc(cred.rawId),
      type: cred.type, response: {clientDataJSON: b64u.enc(cred.response.clientDataJSON),
      attestationObject: b64u.enc(cred.response.attestationObject)}}});
    msg('Passkey created. You can approve now.');
  } catch (e) { msg('Passkey setup failed: ' + e.message); }
}
async function approve(subjectType, subjectId) {
  try {
    const {challenge_id, options} = await post('/v1/approval-challenges',
      {subject_type: subjectType, subject_id: subjectId});
    const o = JSON.parse(options);
    o.challenge = b64u.dec(o.challenge);
    o.allowCredentials = (o.allowCredentials||[]).map(c => ({...c, id: b64u.dec(c.id)}));
    const a = await navigator.credentials.get({publicKey: o});
    const res = await post('/v1/approvals', {challenge_id, credential: {id: a.id,
      rawId: b64u.enc(a.rawId), type: a.type, response: {
      clientDataJSON: b64u.enc(a.response.clientDataJSON),
      authenticatorData: b64u.enc(a.response.authenticatorData),
      signature: b64u.enc(a.response.signature),
      userHandle: a.response.userHandle ? b64u.enc(a.response.userHandle) : null}}});
    document.body.dataset.approvalId = res.approval_id;
    msg('Approved. Approval ' + res.approval_id);
    const place = document.getElementById('place'); if (place) place.hidden = false;
  } catch (e) { msg('Approval failed: ' + e.message); }
}
async function placeOrder() {
  try {
    const key = sessionStorage.getItem('order-key-' + document.body.dataset.approvalId) || crypto.randomUUID();
    sessionStorage.setItem('order-key-' + document.body.dataset.approvalId, key);
    const order = await post('/v1/orders', {approval_id: document.body.dataset.approvalId},
      {'idempotency-key': key});
    const co = await post('/v1/orders/' + order.order_id + '/checkout-sessions');
    document.body.dataset.orderId = order.order_id;
    document.body.dataset.checkoutRef = co.checkout_ref || '';
    msg('Order ' + order.order_id + ' created. Complete the provider step to pay.');
    const pay = document.getElementById('pay'); if (pay) pay.hidden = false;
  } catch (e) { msg('Order failed: ' + e.message); }
}
async function simPay() {
  try {
    await post('/v1/dev/sim/checkouts/' + document.body.dataset.checkoutRef + '/complete', {approve: true});
    location.href = '/orders/' + document.body.dataset.orderId;
  } catch (e) { msg('Simulated payment failed: ' + e.message); }
}
"""


def money(minor: int) -> str:
    return f"R{minor / 100:,.2f}".replace(",", " ")


def when(value: str | datetime) -> str:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt.astimezone(PRESENTATION_TZ).strftime("%a %d %b, %H:%M")


def page(title: str, body: str, *, data: str = "") -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
        f"<body {data}><main><div class='banner'>SIMULATED — NOT REAL MONEY. Fictional stores."
        f"</div>{body}<div id='msg' role='status'></div></main><script>{SCRIPT}</script>"
        f"</body></html>"
    )


def _account(request: Request, c: AppContext):
    return verify(c.session_secret, token_from(request))


@router.get("/dev/login")
def dev_login(token: str, c: AppContext = Depends(dev_only)):
    verify(c.session_secret, token)
    response = RedirectResponse("/wallet", status_code=303)
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
    return response


@router.get("/approve/quote/{quote_id}", response_class=HTMLResponse)
def approve_quote(
    quote_id: uuid.UUID, request: Request, s: Session = Depends(db), c: AppContext = Depends(ctx)
):
    p = _account(request, c)
    if p.kind != "customer":
        return page("Not available", "<h1>Only the account owner can approve.</h1>")
    quote = owned_quote(s, quote_id, p.account_id)
    snap = quote.snapshot
    e = html.escape
    legs = []
    for leg in snap["legs"]:
        lines = "".join(
            f"<li>{ln['units']} × {e(ln['product']['brand'])} {e(ln['product']['name'])}"
            f"{(' ' + e(ln['product']['variant'])) if ln['product']['variant'] else ''}"
            f" — {money(ln['line_total_minor'])}{' <b>(must have)</b>' if ln['must_have'] else ''}"
            f"</li>"
            for ln in leg["lines"]
        )
        legs.append(
            f"<div class='card'><div class='row'><b>{e(leg['seller']['legal_name'])}</b>"
            f"<span>{money(leg['goods_minor'])}</span></div><ul>{lines}</ul>"
            f"<div class='row muted'><span>Delivery {when(leg['delivery']['window_start'])}–"
            f"{when(leg['delivery']['window_end'])[-5:]}</span>"
            f"<span>{money(leg['delivery']['fee_minor'])}</span></div>"
            f"<div class='muted'>{'Stock held by the store' if leg['reservation'] else 'Not reserved'}"
            f"</div></div>"
        )
    policy = snap["fulfilment_policy"] or {}
    if policy.get("mode") == "allow_partial":
        omissions = ", ".join(policy.get("permitted_omissions", [])) or "none"
        policy_text = (
            f"If an item is unavailable, only these may be left out without asking "
            f"you again: {e(omissions)}. Nothing will be added or swapped."
        )
    else:
        policy_text = "Complete basket required: if anything is unavailable, nothing is bought."
    dest = snap["destination"]
    approvable = quote.kind == "firm" and quote.state == "FIRM"
    body = (
        f"<h1>Approve your purchase</h1>"
        f"<div class='muted'>Quote {e(str(quote.id))} · expires {when(quote.expires_at)}</div>"
        f"{''.join(legs)}"
        f"<div class='card'><div class='row'><span>Service fee</span>"
        f"<span>{money(snap['service_fee_minor'])}</span></div>"
        f"<div class='row total'><span>Maximum total</span>"
        f"<span>{money(snap['maximum_payable_minor'])}</span></div>"
        f"<div class='muted'>Delivering to {e(dest['label'])} (address version {dest['version']})"
        f" · paying with {e(snap['funding_source'] or 'not chosen')}</div></div>"
        f"<div class='card muted'>{policy_text} Separate stores cannot give one all-or-nothing "
        f"transaction; if a store fails after paying we handle the cancellation or refund and "
        f"show its progress.</div>"
    )
    if approvable:
        body += (
            "<button class='secondary' onclick='registerPasskey()'>Set up a passkey</button>"
            f"<button onclick=\"approve('quote','{quote.id}')\">Approve with passkey</button>"
            "<button id='place' hidden onclick='placeOrder()'>Place order</button>"
            "<button id='pay' class='secondary' hidden onclick='simPay()'>"
            "Complete simulated payment step</button>"
        )
    else:
        body += f"<div class='card'>This quote is {e(quote.state)} and cannot be approved.</div>"
    return page("Approve purchase", body)


@router.get("/approve/mandate/{grant_id}", response_class=HTMLResponse)
def approve_mandate(
    grant_id: uuid.UUID, request: Request, s: Session = Depends(db), c: AppContext = Depends(ctx)
):
    p = _account(request, c)
    grant = s.get(Grant, grant_id)
    if grant is None or p.kind != "customer":
        return page("Not found", "<h1>Mandate not found.</h1>")
    body = (
        "<h1>Approve agent mandate</h1><div class='card'><ul>"
        f"<li>Per order up to {money(grant.per_order_cap_minor)}</li>"
        f"<li>Up to {money(grant.period_cap_minor)} every {grant.period_days} days</li>"
        f"<li>At most {grant.max_orders_per_day} orders a day</li>"
        f"<li>Only to your approved address version</li>"
        f"<li>Valid until {when(grant.valid_until)}</li></ul>"
        "<div class='muted'>Test fixture only. Revocable at any time.</div></div>"
        "<button class='secondary' onclick='registerPasskey()'>Set up a passkey</button>"
        f"<button onclick=\"approve('mandate','{grant.id}')\">Approve with passkey</button>"
    )
    return page("Approve mandate", body)


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_page(
    order_id: uuid.UUID, request: Request, s: Session = Depends(db), c: AppContext = Depends(ctx)
):
    from app.orders.status import order_status

    p = _account(request, c)
    try:
        st = order_status(s, order_id, p.account_id)
    except TrollieError:
        return page("Not found", "<h1>Order not found.</h1>")
    m = st["money"]
    legs = "".join(
        f"<li>{html.escape(lg['leg_id'])}: {html.escape(lg['state'])}"
        f" · delivery {html.escape(str(lg['delivery']))}</li>"
        for lg in st["legs"]
    )
    body = (
        f"<h1>Order {html.escape(st['state'])}</h1><div class='card'>"
        f"<div class='row'><span>Bank hold</span><span>{money(m['bank_hold_minor'])}</span></div>"
        f"<div class='row'><span>Charged</span><span>{money(m['charged_minor'])}</span></div>"
        f"<div class='row'><span>Refund requested</span>"
        f"<span>{money(m['refund_requested_minor'])}</span></div>"
        f"<div class='row'><span>Refund confirmed</span>"
        f"<span>{money(m['refund_confirmed_minor'])}</span></div>"
        f"<div class='muted'>{html.escape(m['bank_hold_note'] or '')}</div></div>"
        f"<div class='card'><ul>{legs}</ul></div>"
    )
    return page("Order status", body)


@router.get("/merchant", response_class=HTMLResponse)
def merchant_harness(s: Session = Depends(db), c: AppContext = Depends(dev_only)):
    """Thin local stand-in for a merchant portal (DECISIONS.md D-S04)."""
    rows = []
    for leg in s.scalars(
        select(OrderLeg)
        .where(OrderLeg.state.in_(["ACCEPTED", "READY_FOR_COLLECTION", "COLLECTED"]))
        .order_by(OrderLeg.created_at)
    ):
        job = s.scalars(select(DeliveryJob).where(DeliveryJob.order_leg_id == leg.id)).first()
        order = s.get(Order, leg.order_id)
        actions = []
        if leg.state == "ACCEPTED":
            actions.append(
                f"<button onclick=\"post('/v1/dev/merchant/legs/{leg.id}/ready')"
                f'.then(()=>location.reload())">Mark ready</button>'
            )
        if job and leg.state == "READY_FOR_COLLECTION":
            actions.append(
                f"<button class='secondary' onclick=\"post('/v1/dev/courier/jobs/"
                f"{job.id}/collected').then(()=>location.reload())\">Courier collected"
                f"</button>"
            )
        if job and leg.state == "COLLECTED":
            actions.append(
                f"<button class='secondary' onclick=\"post('/v1/dev/courier/jobs/"
                f"{job.id}/delivered').then(()=>location.reload())\">Delivered</button>"
            )
        rows.append(
            f"<div class='card'><b>{html.escape(leg.leg_id)}</b> · order "
            f"{html.escape(str(order.id))[:8]} · {html.escape(leg.state)}"
            f"{''.join(actions)}</div>"
        )
    return page(
        "Merchant harness",
        "<h1>Merchant harness (simulated)</h1>"
        + ("".join(rows) or "<div class='card'>No open legs.</div>"),
    )


@router.get("/wallet", response_class=HTMLResponse)
def wallet_page(request: Request, s: Session = Depends(db), c: AppContext = Depends(ctx)):
    from app.wallet import service as wallet

    p = _account(request, c)
    try:
        with s.begin():
            w = wallet.wallet_for(s, p.account_id)
            b = wallet.balances(s, w.id)
    except TrollieError:
        return page(
            "Wallet",
            "<h1>No wallet yet.</h1><div class='card'>Signed in as account "
            f"{html.escape(str(p.account_id))}.</div>",
        )
    envelopes = "".join(
        f"<div class='row'><span>Envelope {html.escape(k[:8])}</span><span>{money(v)}</span></div>"
        for k, v in b["envelopes_minor"].items()
    )
    body = (
        f"<h1>Wallet</h1><div class='card'>"
        f"<div class='row total'><span>Total</span><span>{money(b['total_minor'])}</span></div>"
        f"<div class='row'><span>Available (unallocated)</span>"
        f"<span>{money(b['unallocated_minor'])}</span></div>{envelopes}"
        f"<div class='row'><span>Reserved for purchases</span>"
        f"<span>{money(b['reserved_minor'])}</span></div>"
        f"<div class='row'><span>Frozen</span><span>{money(b['frozen_minor'])}</span></div>"
        f"<div class='row muted'><span>Pending top-ups (not usable)</span>"
        f"<span>{money(b['pending_topups_minor'])}</span></div></div>"
        f"<div class='muted'>Funding reference {html.escape(w.funding_reference)}</div>"
    )
    return page("Wallet", body)
