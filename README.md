# PumpGrok v4 — Desk Status Adapter / Read-only Market Monitor

## What is genuinely connected now

The standalone terminal now calls the **installed supported operational CLI** on
its own host, using fixed read-only commands, no shell and no direct engine DB reads:

```text
pumpgrok doctor
pumpgrok state status --seat chief
pumpgrok killswitch status
pumpgrok ticket list
pumpgrok report --daily
```

At verification on 9 November 2026, Asia/Dhaka:

- Same-host adapter: **CONNECTED READ-ONLY / HALTED / effective mode paper**.
- Actual ledger kill switch is active; no halt was cleared or state changed.
- Engine equity: **10 SOL**, zero trades, zero open positions; ledger sequence 3.
- Engine report says autonomy `autonomous-paper`; this is reported state only,
  **not activated or adopted by the UI**. No desk runner was started.
- Installed logs report max-trade fraction 0.02, equity basis 10 SOL,
  max positions 3 and slippage 300bp. This is not verification of the agreed
  **$50 capital / $2.50 USD trade limit**. The mismatch remains visible and blocking.
- Doctor exits 0 for module availability, but explicitly reports gateway and
  reports module not implemented, and no health server. This is **not** a complete
  prompt/skills/roster/grants health proof. The supported daily report wrapper does
  work despite the separate reports-module warning.
- No ticket-scoped full RISK read/exact approval gateway is exposed by the
  documented CLI root help; doctor confirms the gateway is not implemented.
  The read adapter never invents missing evidence or calls a write command.
  CLI `paper buy` / `paper sell` write entrypoints do exist, but require a consumed
  approval ID and SOL sizing; these are not a supported read interface proving
  the missing ticket risk, owner approval and agreed USD policy. They were not run.
- All ten assistant Bots remain **NOT CONNECTED**. The engine report has no
  heartbeats, no market ticks and no recorded risk verdicts. Roster names are not
  actual activity or live assistant connections.

The engine **SOL ledger** and the standalone modeled **USD $50 ledger** are
separate. They are displayed separately, never added or converted, and no fake
USD-to-engine integration is claimed.

## Start / Stop that really does something

**Start Market Monitor** reads real public DexScreener profiles and exact-mint
pairs. A native Streamlit timed fragment checks every 30 seconds while the user
session is active. **Stop Market Monitor** disables further monitor market reads.
There is no daemon, scheduler, detached scan job or autonomous order loop.

Successful-read and attempt counters count actual completed requests, not
animations. The panel shows source health, last retrieval time/age, actual pairs
and real code-stage logs. HTTP Date/Age are preserved; source market-event time
remains UNKNOWN. No cached response is promoted into a fresh execution quote.
Shared SQLite cooldown prevents multiple tabs/reruns from spamming discovery.
Access-denied providers are stopped without alternate endpoints/proxy bypasses.

The real-source verification cycle observed eight pairs, then Stop made zero
additional provider reads. This is source connectivity evidence, not a trade,
backtest, profit result or full RISK clearance.

Manual **Run Scanner Cycle**, selected mint refresh, finalized authority audit and
Jupiter quote-only reads remain available subject to provider health. No network
transaction is constructed: Jupiter requests omit taker and reject transaction
or wallet-bearing responses. The quote is informational, not guaranteed execution.

## Why paper fills are still blocked — concrete engine facts

The previous custom signing bridge was not an installed supported desk interface.
It has been **removed**, not provisioned. No Ed25519 signer, signature file, custom
private key, seed, binding-key read or manufactured signed CLEAR is used. Paper
simulation is keyless ledger bookkeeping.

The local modeled broker remains implemented and tested: exact manual owner
approval binding, fresh route model, atomic append-only SQLite order/fill rows,
partial/full exits, positions, fees, average cost basis, realized/unrealized P&L,
equity/drawdown, daily latches, concurrent idempotence and UNKNOWN RESULT
reconciliation. Valid paths are tested only through isolated keyless Python test
providers, which are never a deployed file/checkbox bypass.

Production currently stops at the supported operational adapter because:

1. The actual desk is halted.
2. Actual engine risk units/defaults have not been reconciled to the owner's USD
   policy by a sanctioned owner procedure.
3. Installed runtime lacks the supported full scoped RISK/exact approval gateway
   needed to connect the terminal to genuine paper execution. Status is not proof
   of risk, owner approval or strategy promotion. No paper commands are invoked.
4. Recorded-market strategy replay/human promotion and owner-authenticated exact
   ticket flow still need genuine integration. Anonymous Cloud visitors cannot
   approve/place. Existing owner OIDC controls are not disabled for convenience.
5. All ten actual assistants need sanctioned identity/heartbeat/work-routing
   integration; no peer messaging or fake Bot orchestration is performed here.

Clearing the halt alone would not resolve the missing interface, USD policy or
approval evidence. This package does not clear it or supply an unsafe shortcut.
No guaranteed profitability is claimed.

## Same host versus Streamlit Community Cloud

### Same trusted host — read integration is working

The terminal embeds the adapter, so no helper import/package is needed. Defaults:

```text
PUMPGROK_CLI=/workspace/pumpgrok/.venv/bin/pumpgrok
PUMPGROK_DESK_DIR=/workspace/pumpgrok
```

Optional environment settings can select another owner-provisioned installation,
using absolute trusted local paths. The executable must be owner/root-owned,
executable and not group/world-writable. Only the five fixed commands above are
allowed. Source timestamps, exit codes and stdout hashes accompany the reads;
stale, contradictory, malformed or failed status is UNKNOWN, never clear.
The child environment excludes only the terminal's five independent UI/adapter
settings, because the installed engine rejects unknown `PUMPGROK_*` names. All
engine mode/policy/safety settings are retained unchanged. No `--mode paper` override
masks the actual effective mode. A live-mode report
stops the monitor and paper flow for escalation.

Optional diagnostic (the app does not depend on this helper):

```bash
python desk_status_adapter.py
```

### Current Community Cloud app

Your Cloud app is on a **different machine** from the installed box engine. Files
at `/workspace/pumpgrok` on this box are not present at
`/mount/src/deskbuilder` on Community Cloud. A Python import, filename, checkbox or
missing local kill file cannot connect the two machines or prove clearance.
The Cloud app therefore reports an exact DISCONNECTED reason while its public
market monitor can still work. No tunnel, API server, public backend exposure or
network security change is made.

An actual remote connection needs a supported authenticated engine gateway on a
chosen host. The installed engine reports that gateway **not implemented**; this
is an engine capability blocker, not a missing custom signing key. Alternatively,
co-locate terminal and engine for the already-working read-only integration.
Neither hosting choice alone enables full paper trading: engine interface/policy/
owner approval integration must be completed through sanctioned project tooling.

Minimal owner decision: keep Community Cloud as a real-market monitor for now, or
choose a trusted co-located engine/terminal deployment for desk status integration.
A full remote paper-trading deployment additionally needs an actual supported
engine gateway implementation and durable storage. No deployment/account/secret
has been configured here.

## Run and deploy — still only two required files

```text
trading_terminal.py
requirements.txt
```

Python 3.11+ recommended. No helper folder is required. Optional
`.streamlit/config.toml` supplies native dark controls; inline styling works alone.

```bash
python -m pip install -r requirements.txt
python -m streamlit run trading_terminal.py
```

Windows: use `py` instead of `python` where needed. On this box, the existing venv
command is:

```bash
cd /workspace
/workspace/.terminal-venv/bin/python -m streamlit run trading_terminal.py
```

The existing detached process is already running on port 8501; do not start a
second copy unnecessarily. Local health responding does **not** prove a remote
browser or Grok Bot desktop can open the URL. Browser testing was blocked/refused;
no screenshot, exact video match or accessible native preview is claimed. No
browser network policy/proxy/port workaround was attempted. Box doctor reported
11 checks passing; that does not override browser restrictions.

For Community Cloud, replace both ROOT files in the existing repository and reboot
with main path `trading_terminal.py`. Look for:

**Desk Status Adapter v4 • Read-only Monitor • English / Dark • Single File**

This package makes no GitHub edits or Cloud deployment. AppTest does not prove
that the existing website has received the new files.

## Preserved local paper safeguards

- $50 paper capital, $2.50 maximum action notional, 3% slippage cap, three positions,
  $2.50 daily realized-plus-unrealized loss entry halt, Asia/Dhaka daily boundaries.
- Active mint/freeze authority and Token-2022 transfer tax forbidden; unknown
  mandatory evidence blocks. Authority/extension code checks alone are not full RISK.
- Modeled route output: adverse 25bp plus estimated extra 30bp + $0.01 cost reserve;
  never actual execution or on-chain simulation. Known nonzero network fees block
  until verified fresh SOL/USD cost conversion exists. Missing liquidity/route/fees,
  stale source, depeg, excessive impact/slippage and wrong identity block.
- New exact quote and manual authenticated approval for every partial/full exit.
  No random profit or immediate fabricated exit. Entry filters are unpromoted
  research rules, not a profitable strategy or authority for automated tickets.
- Append-only event hash chain with startup reconciliation; observations/drafts
  never become fills. Decimal money/quantity arithmetic; no duplicated rerun trade.
  Ambiguous I/O means reconcile, never automatic second-send.
- CSV/JSONL and portfolio/drawdown exports remain available. Default DB path is
  `terminal_data/terminal.sqlite3`; optional `PUMPGROK_TERMINAL_DB` selects a durable
  writable mounted location. Cloud local disk can disappear: this is not durable
  hosted custody, and losing it loses local loss latches/history. Keep backups.

## Tests and evidence

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

The existing broker coverage was retained with keyless isolated fixture providers.
Additional tests use **recorded supported CLI read outputs**, including halt/policy/
portfolio facts, timeout/invalid/stale/conflicting/live/fake-capability handling,
Cloud disconnection, fixed no-shell read allowlist, no key provisioning, real read
counting, Start/Stop and native two-file Streamlit AppTest. No fixture is genuine
trading performance and no test mutates engine state.

See `evidence/receipt.json`, `tests.txt`, `adapter-live.json`,
`real-monitor-smoke.json`, CLI command receipts and `box-doctor.txt`.
No database, private key, token, secret, cache or virtualenv is included in the ZIP.

Official API references retained by the app:
- https://docs.dexscreener.com/api/reference
- https://solana.com/docs/rpc/http/getaccountinfo
- https://www.solana-program.com/docs/token-2022/extensions
- https://dev.jup.ag/api-reference/swap/v2/order
- https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment
