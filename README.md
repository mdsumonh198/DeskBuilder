# PumpGrok Paper System v3 — English / Dark / Single File

This is now an implemented local **modeled paper broker**, not only a scanner UI.
It is **not activated for real-source fills**: the actual desk halt is active, the
sanctioned gate bridge is absent, effective policy agreement is unverified, and
full RISK/rule-promotion evidence is missing. No runtime fill was approved or placed.
There are no wallets, transaction construction, chain simulation, signing,
broadcasting, live order endpoints, autonomous scans, schedules or real money.
All ten actual assistant Bots remain **NOT CONNECTED**.

## Deploy using only two files

Required at the app root:

```text
trading_terminal.py
requirements.txt
```

No helper package, local module, repository checkout, encoded bundle, `eval` or
`exec` is needed. Python 3.11+ recommended. Optional `.streamlit/config.toml`
sets the native theme; inline CSS supplies readable dark defaults without it.

### Local Linux/macOS

```bash
cd /path/to/extracted/folder
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run trading_terminal.py
```

If your environment is already installed:

```bash
streamlit run trading_terminal.py
```

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run trading_terminal.py
```

Open the local URL printed by Streamlit. `localhost` points to the machine
running Streamlit, not another computer. No public tunnel is configured.

### Streamlit Community Cloud

1. Replace **both root files** in your existing app repository. The ZIP itself
   is not an entrypoint. Do not merely refresh the old app.
2. Set main file path to `trading_terminal.py` and reboot/redeploy so updated
   requirements install. The optional `.streamlit/config.toml` goes at root.
3. Look for **Paper System v3 • English / Dark • Single File**.
4. Start with **Run Scanner Cycle**. It reads public Solana pair observations.
5. Authority evidence and route quotes are explicit read-only button actions.
   **A working scanner or quote is not authorization to fill an order.**

Actual Community Cloud deployment is not verified by the local AppTest.
Never expect an absent box-local halt file on Cloud to mean the desk is clear.

## What the implemented code does

- Real DexScreener latest-profile discovery and exact-mint/pair observations;
  source URLs, fetched UTC, HTTP Date/Age and separate UNKNOWN market event time.
  No fake price or synthetic fallback. The discovery universe is not all launches.
- Public finalized Solana `getAccountInfo` with parsed mint-program/authority/
  initialization/decimals checks and conservative Token-2022 extension parsing.
  A passing subset is **not** a complete RISK Bot verdict. Unknown parser,
  extension inventory, mutable tax, hook, permanent delegate or other unsupported
  security extension blocks fills. Active mint/freeze authority and positive
  older/newer transfer-fee schedules are forbidden.
- Genuine Jupiter Swap v2 **quote-only** requests without a `taker`. Unexpected
  wallet/transaction fields reject the response. Fee, mint, exact input amount,
  route graph/allocation, output atomic units, impact, expiry and provenance are
  checked. Public unauthenticated reads worked during the receipt run despite
  documentation listing an API key. No market API credential is configured or required by
  this build. If the host later requires auth, requests stop; an owner-authorized
  read-only credential integration would be a separate step, never a bypass.
- **Quote → local deterministic simulation → exact approval → atomic local fill**
  is executable code. Genuine route output is still informational, not a promise
  of execution. This is a MODELED fill: 25bp adverse buffer, plus an additional
  conservative estimated 30bp + $0.01 fee reserve. Route fees are already reflected
  in route output; the additional reserve deliberately overstates ancillary costs.
  No actual network/gas fee or chain landing is asserted. Nonzero quoted network/rent
  fees are rejected until a fresh verified SOL/USD cost-conversion adapter exists;
  the fixed reserve is never silently substituted for known large gas costs. USDC is assumed near $1;
  source USD deviation above 0.5% blocks. BUY budgets use nominal USDC units.
- Known pool liquidity ≥ $10,000 and size ≤ 0.1% of pool liquidity are required.
  A real route quote at exact size is depth-at-size evidence, **not** a complete
  orderbook/liquidation-depth audit. Missing route/liquidity/fee evidence blocks.
- SQLite `paper_events_v1` is additive and independent of old research observations,
  draft tickets and legacy cash. Old observations never become fills. Genesis is
  exactly $50 simulated cash, no seed profit or fabricated trade history.
- Append-only triggers, contiguous sequence/hash-chain validation and replayed
  approval/position/basis/cash reconciliation run at startup/read. Decimal strings
  (USD rounded to 8 decimal places, quantity bounded to mint precision) avoid SQL
  floating-point cash drift. Every approval, order, fill, mark, equity valuation,
  withdrawal and halt is auditable. Fill records carry source quote URLs and
  verified gate evidence/signature/public verification key for later audit.
- `BEGIN IMMEDIATE` plus unique decision IDs serializes competing sessions. A
  repeat successful decision returns the committed original fill, not a second
  order. Binding changes, stale/withdrawn/missing approvals block. Ambiguous I/O
  becomes **UNKNOWN RESULT**: read-only reconcile by decision id; never auto-retry.
- BUY deducts notional plus modeled fee; partial/full SELL uses a new fresh quote,
  weighted average cost basis and modeled proceeds minus fees. Positions survive
  restarts. Overselling, negative cash and extra seed capital are rejected.
- Fees, realized/unrealized P&L, gross-before-charged-fees/net marked equity,
  estimated remaining exit costs, daily loss and peak-to-current drawdown are
  separate. Indicative marks do not guarantee liquidation equity. Missing marks
  yield UNKNOWN equity; stale marks are explicitly not fresh and block new entries.
- CSV/JSONL exports for all events/orders/approvals/fills/marks/equity, plus a JSON
  portfolio/drawdown summary. Research observations remain separate in SQLite.

## Limits and strategy rules

Exact owner limits: $50 initial paper capital, $2.50 maximum notional **per BUY or
SELL action**, 3% maximum adverse slippage, three concurrent mints, and a $2.50
daily realized-plus-unrealized loss entry halt. The cap is not a fixed 3% loss
applied to every fill. Repeated adds cannot pyramid a mint beyond the conservative
$2.50 basis limit. Fees may make an initial $2.50 order's basis slightly higher.

Daily boundaries are **Asia/Dhaka (UTC+6)**. The prior recorded fresh daily close
sets next day's baseline, conservatively never below $50. This is manually sampled
valuation, not a guaranteed midnight mark. The first baseline is $50. A $2.50 loss
latches entries for that calendar day, even if marks later recover, across reruns,
new tabs and process restarts while the ledger file remains. No reset button exists.
Global halt overrides BUY and SELL; the daily entry halt alone does not authorize
an exit or bypass other gates. Stale marks block entries; exact fresh SELL quotes
are still mandatory. No continuous risk monitor is running. Drawdown uses the
highest recorded fresh net equity (at least $50); a zero denominator is UNKNOWN,
never infinity or an invented percentage.

Research entry filter: observed liquidity ≥ $10,000 and 1h volume ≥ $1,000.
Proposed -10% stop / +20% take-profit are **research notes only**, not automatic
orders or approved strategies. Missing fields are BLIND. Passing unit fixtures
is software validation, **not market replay, a profitable backtest or permission
for strategy promotion**. Recorded-market replay and explicit human promotion
must precede real-source paper tickets. No win-rate or video ROI claim is copied.

## Genuine activation/integration prerequisites — currently NOT satisfied

This package does not contain or install a bridge into the real desk. It cannot
clear the halt, modify risk policy or claim other assistant activity.

1. Owner authorizes a sanctioned read-only integration from the actual desk.
2. Owner uses the desk's separate human procedure for any halt/config changes.
   The active halt is NOT cleared by this app. Reported legacy effective defaults
   must be reconciled to the exact USD policy; editing a note is not verification.
3. That integration publishes short-lived Ed25519-signed **public gate attestations**
   from authoritative current state, full RISK evidence and genuine owner receipts.
   Only a public verification key is used here; this app has no signing key.
   Do not generate your own fake CLEAR file or enable a TEST fixture in deployment.
4. Genuine recorded replay + human rule/model promotion and mint/pair/audit-scoped
   full RISK CLEAR, including holder/social/all mandatory checks, must be evidenced.
5. Fresh real source market, authority subset and quote must pass together.
6. Provision owner-only Streamlit OIDC access through the supported authentication
   setup (Authlib is declared). Set public identity selectors `PUMPGROK_OWNER_ISSUER`
   and `PUMPGROK_OWNER_SUBJECT` to the owner. The signed bridge must bind
   `owner_identity_hash = sha256(canonical({issuer, subject}))`. The app reads only
   verified identity claims, checks issuance/expiry/not-before, and never reads or
   displays raw tokens. No authentication is provisioned by this package. The
   native Owner Sign-In button requires separately owner-approved OIDC configuration.
   An anonymous public visitor cannot approve or place even if all market gates pass.
7. The authenticated owner inspects the exact proposal, types `CONFIRM PAPER <decision_id>`, presses
   **Approve Exact Paper Ticket**, then separately **Place Approved Simulated Order
   ONCE** before quote/approval expiry (≤30 seconds). Approval binds the entire
   ticket, mint/pair/side/amount/quantity/slippage/quote version+expiry/audit/rule/id.
   No automatic-paper authority is inferred from historical engagement notes.

Read-only verifier contract for future sanctioned integration:

- `PUMPGROK_GATE_ATTESTATION`: path to an envelope with `payload` and base64 `signature`.
- `PUMPGROK_GATE_PUBLIC_KEY`: owner-provisioned hex Ed25519 **public verification** key.
  These are integration configuration, not UI bypass switches or wallet credentials.
- Signature covers canonical sorted compact ASCII JSON (`canonical(payload)`).
- Required payload: audience `pumpgrok-standalone-paper-v3`, issued UTC within 30s,
  expires UTC in the future and within 60s, `authoritative: true`, authoritative
  `halt: CLEAR`, nonempty evidence/owner-authorization receipt IDs, a 64-hex `owner_identity_hash`, exact `POLICY`,
  strategy version `RULES`, replay/human promotion true and exact `MODEL`.
- `risk[mint]` must carry exact pair, current authority `audit_id`, `verdict: CLEAR`,
  and true holders/social/all-mandatory evidence flags. These are signed facts from
  a sanctioned bridge, never values a UI checkbox can assert.
- Presence of `/workspace/pumpgrok/var/desk/KILLSWITCH` wins even over signed evidence.
  Absence is not clearance: missing/invalid/stale signatures still block everything.
- Full exact schemas and validation logic are readable in `DeskEvidence.read` and
  `PaperBroker._checks`. Upstream bridge implementation/integration remains a blocker;
  there is no claim that signing an arbitrary local document proves real desk state.

## Persistence and backup

Default: `terminal_data/terminal.sqlite3` beside the script. Set
`PUMPGROK_TERMINAL_DB` to a writable durable mounted-volume path on a suitable host.
The new event table is additive; existing observations/drafts are preserved.
Back up the SQLite file with a proper SQLite backup/snapshot while running and
export JSONL/CSV regularly. No DB, secret, cache, virtualenv or test signer is
included in the ZIP. Disk-administrator tampering/truncation is not magically
prevented by a local hash chain; retain independent exported heads/backups.

**Streamlit Community Cloud local storage can disappear** during instance
replacement/redeploy. Losing the file loses history, approvals and local daily
latches. This is not a hosted durable production database. Do not enable a gated
paper deployment on ephemeral disk without an owner-approved durable persistence
and recovery design. Disconnected Cloud defaults always remain blocked.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Tests use temporary isolated TEST ledgers and engineered deterministic provider
fixtures; their returns are not investment performance. Test-only non-wallet
attestation signers exercise signature verification, and never ship a private key.
The deployment test begins with only the two required files, no helper package or
project PYTHONPATH, and exercises Streamlit AppTest twice. Optional read-only smoke:

```bash
python tests/smoke_public_reads.py
```

It probes documented providers once each, stops failures, and records a local model
**preview**, never an approval/order/fill. See `evidence/receipt.json`, test output,
and `evidence/public-read-smoke.json`. Actual real-source fill validation is blocked
by genuine desk gates, not faked by testing. Existing local Streamlit health may be
OK without proving the user's remote browser can access it.

Official documentation:
- https://docs.dexscreener.com/api/reference
- https://solana.com/docs/rpc/http/getaccountinfo
- https://www.solana-program.com/docs/token-2022/extensions
- https://dev.jup.ag/api-reference/swap/v2/order
- https://docs.streamlit.io/develop/api-reference/user/st.user
