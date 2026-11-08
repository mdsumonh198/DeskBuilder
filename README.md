# Market Scanner v2 • English / Dark

**This is the current real-data application, not the previous synthetic demo.**
The UI is English-only, with a deep navy/cyan/emerald crypto terminal theme.
Verify the visible version marker: `Market Scanner v2 • English / Dark`.
All ten assistant Bots remain NOT CONNECTED, and all paper fills remain EXECUTION LOCKED.
A new database starts with $50 paper capital and no trades or invented profit.

## Updating an older deployment

Download and extract the complete ZIP, then replace **all** application files:
`trading_terminal.py`, `requirements.txt`, `market_paper_terminal/`, and the root
`.streamlit/config.toml`. Keep the helper package alongside the entrypoint.
Do not just replace an old screenshot/demo file or refresh an unchanged deployment.
The ZIP contains no private database, credentials, environment or old demo backups.
If you already have a real research SQLite database, preserve it; the UI presents
legacy localized entries in English without altering the original evidence.
Never import the old synthetic demo ledger as real market results.

### Windows Terminal / PowerShell

Open Terminal in the extracted folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run trading_terminal.py
```

This does not require PowerShell script activation. Open the Local URL printed by
Streamlit, normally http://localhost:8501 on that Windows computer. Stop the old
app with Ctrl+C before starting the replacement on the same port.

### Streamlit Community Cloud

1. Replace all app/module/requirements files in your deployment's existing source
   repository, including `.streamlit/config.toml` in its root. Upload source files,
   not the ZIP as the app entrypoint. No personal runtime database or secrets are needed.
2. Set the main file path to `trading_terminal.py` and install `requirements.txt`.
3. Redeploy/reboot the app so the dark theme configuration is loaded, then hard-refresh.
4. Confirm the new English/Dark version marker, real sources, $50 new-account
   paper cash, and execution-lock notice. Old synthetic trades must not appear.

The cloud filesystem may reset on redeploy/reboot; SQLite durability only applies
while its file is retained. Use a properly managed persistent volume/store before
relying on hosted history across instance replacement. This package does not add one.

The shipped `.streamlit/config.toml` applies only in your extracted deployment
root. No shared global config or browser/proxy settings were changed on the box.
The existing root app additionally supplies dark CSS and explicitly dark charts/cells.

---

# PumpGrok real-market research terminal — paper execution LOCKED

This replaces the previous synthetic demo. It is a working **real public market scanner and durable research-ticket UI**, not a completed paper trading desk/broker integration.

## Run
From the folder containing `trading_terminal.py`:

```bash
python3 -m venv .terminal-venv
source .terminal-venv/bin/activate
pip install -r requirements.txt
streamlit run trading_terminal.py
```

Existing box environment: `cd /workspace && source .terminal-venv/bin/activate && streamlit run trading_terminal.py`.
The already-running box service uses port 8501; do not start a second instance on that port. Refresh its page to load the new application.

Keep `market_paper_terminal/` beside the entrypoint. SQLite automatically initializes at `market_paper_terminal/data/terminal.sqlite3`. Optional `PUMPGROK_TERMINAL_DB` selects a separate local research database (useful for tests). No credentials, wallet, or account connection required.

## What really works
- Native Run Scanner Cycle issues read-only documented DexScreener requests:
  - `GET https://api.dexscreener.com/token-profiles/latest/v1`
  - `GET https://api.dexscreener.com/tokens/v1/solana/{comma-separated-mint-addresses}`
- Latest Solana profiles discover up to eight exact 32-byte base58 mints; pair records must match those base mints. Profiles are not an exhaustive market scan or guaranteed latest launch feed; token symbols/names are unverified labels, not identity.
- Provider price, liquidity USD, hour-volume USD, venue, exact mint/pair, source URL, JSON field provenance, HTTP cache metadata, and retrieval UTC are retained. Missing values stay missing/BLIND. No synthetic fallback.
- Only user clicks fetch; global SQLite 30-second cooldown avoids request flooding across sessions. Cached reruns do not add scanned counts. Unique observed pair count is not a cumulative fake scan counter. Identical snapshots deduplicate persistently.
- Code actions are logged in English with Asia/Dhaka timestamps; all ten assistant seats explicitly show NOT CONNECTED. Code scanner actions are not falsely attributed to Bots.
- Provider errors retain last-good observations and their original fetch times. HTTP 403/451, proxy denial or explicit block latches requests off; no alternate network route is attempted. No automatic retry.
- Observations older than 60 seconds are STALE. “Recent retrieval” is not proof that a price itself is recent: the API does not provide an observation timestamp. Single-provider marks are NOT independently corroborated and NOT executable quotes.
- Durable, idempotent local research drafts capture exact mint, pair, side, USD size and maximum slippage. They are NOT approved tickets or fills.
- Distinct new ledger initializes with exactly $50 illustrative paper cash, no trades, no positions, no fees, no gains. Old synthetic history is not imported or reused.

## Why trades remain locked
This app does not implement an alternative broker around the real desk's halt. `/workspace/pumpgrok/var/desk/KILLSWITCH` is checked by presence only, read-only. Missing file means UNKNOWN, never “clear.” No engine source/configuration/key files are opened or modified.

All paper buys **and sells** are unconditionally locked because the desk execution adapter is absent. The UI additionally explains the actual halt, unverified effective configuration, absent executable quote/simulation, missing exact human approval and BLIND mandatory audit evidence. There is no enable/clear-halt/live toggle.

The owner limits represented in validation are $50 paper capital, $2.50 maximum trade, 3% maximum slippage, at most three open positions, and a $2.50 daily realized-plus-unrealized loss entry freeze. Active mint/freeze authorities or Token-2022 transfer tax are forbidden. This does **not** prove the real engine has matching settings. The app does not infer permission from an autonomous-paper configuration note.

DexScreener does not supply genuine mint/freeze/Token-2022 extension audit or holder/cluster/social/route evidence. These are explicitly BLIND and block execution. “Confirmed rugs blocked” remains zero; missing evidence is not proof of a rug.

### Remaining integration work (not completed)
Sanctioned core engine connection; authoritative engagement/halt/config agreement; genuine risk/holder/social evidence; fresh same-mint executable route/depth/fee quote; quote → simulate → exact manually approved idempotent paper fill; restart reconciliation; portfolio marks/unrealized P&L and fee accounting; daily loss tracking on actual paper positions. Until then, the chart contains only the initial paper capital point. No real or paper order-placement implementation exists here.

## Verification
```bash
python -m unittest market_paper_terminal.test_core
python -m market_paper_terminal.test_app
python -m py_compile trading_terminal.py market_paper_terminal/core.py
```
Offline tests use isolated temporary databases and explicitly named fixtures, never production fake-market fallbacks. Checks cover parsing, missing/malformed data, same-mint filtering, stale evidence, error retention, blocked-provider stop, cooldown, snapshot/draft deduplication across reopen, limits, global-halt no-bypass and Streamlit initial/scan/draft behavior without fills.
`network-smoke.json` records one genuinely successful public read made during setup. It is timestamped historical evidence, not a live feed or a seed fallback. Source archive excludes runtime DB, old demo code and environment.

Official API documentation: https://docs.dexscreener.com/api/reference

No browser accessibility or visual-rendering verification is claimed from HTTP health alone.
