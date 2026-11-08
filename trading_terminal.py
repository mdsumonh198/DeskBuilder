"""PumpGrok — isolated, synthetic paper terminal. No desk or network integrations."""
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='PumpGrok • Paper Terminal', page_icon='◈', layout='wide')
TZ = ZoneInfo('Asia/Dhaka')
ROLES = {'CHIEF': 'Cycle orchestrator', 'SCOUT': 'Pair discovery', 'RISK': 'Safety gate',
         'WHALE': 'Holder analysis', 'SNIPER': 'Synthetic fills', 'RUG': 'Threat detection',
         'EXIT': 'Synthetic close', 'SHILL': 'Narrative context', 'SIGNAL': 'Momentum score', 'JOURNAL': 'Paper ledger'}
INITIAL = 10000.0

def now():
    return datetime.now(TZ)

def event(state, agent, text, stamp):
    state['activity'].append({'Time (UTC+6)': stamp.strftime('%H:%M:%S'), 'Agent': agent, 'Simulated activity': text})

def cycle(state):
    """A deterministic per-cycle synthetic scan with two blocks and two round trips."""
    state['cycle'] += 1
    n = state['cycle']
    rng = random.Random(7300 + n)
    stamp = now()
    event(state, 'CHIEF', f'DEMO cycle {n:03d} opened • isolated simulation', stamp)
    rows = []
    for i in range(6):
        symbol = f'DEMO-{n:03d}-{i+1:02d}'
        blocked = i in (1, 4)
        filled = i in (0, 3)
        price = round(rng.uniform(.015, .95), 6)
        score = rng.randint(68, 96) if not blocked else rng.randint(12, 39)
        reason = ('Synthetic concentration flag' if i == 1 else 'Synthetic liquidity flag') if blocked else ('Round trip closed' if filled else 'Below entry threshold')
        rows.append({'Cycle': n, 'Demo pair': symbol, 'Synthetic price ($)': price,
                     'Score': score, 'Decision': 'BLOCKED' if blocked else ('PAPER FILLED' if filled else 'WATCH'),
                     'Reason': reason, 'Time (UTC+6)': stamp.strftime('%H:%M:%S')})
        event(state, 'SCOUT', f'{symbol} discovered at synthetic ${price:.6f}', stamp)
        event(state, 'RISK', f'{symbol}: {"BLOCK" if blocked else "DEMO CLEAR"}', stamp)
        if blocked:
            state['blocked'] += 1
            event(state, 'RUG', f'{symbol}: hypothetical threat blocked before entry', stamp)
            continue
        event(state, 'WHALE', f'{symbol}: simulated holder check complete', stamp)
        event(state, 'SHILL', f'{symbol}: synthetic narrative reviewed; no social data', stamp)
        event(state, 'SIGNAL', f'{symbol}: demo score {score}/100', stamp)
        if not filled:
            continue
        allocation = round(min(500.0, state['balance'] * .05), 2)
        # Net return includes illustrative 0.2% round-trip fees; never a real quote.
        gross_return = rng.uniform(-.035, .065)
        fee = round(allocation * .002, 2)
        pnl = round(allocation * gross_return - fee, 2)
        exit_price = round(price * (1 + gross_return), 8)
        state['balance'] = round(state['balance'] + pnl, 2)
        state['trades'].append({'ID': f'P-{n:03d}-{i+1:02d}', 'Demo pair': symbol,
            'Entry ($)': price, 'Exit ($)': exit_price, 'Notional ($)': allocation,
            'Fees ($)': fee, 'Net P&L ($)': pnl, 'Status': 'PAPER CLOSED',
            'Time (UTC+6)': stamp.strftime('%H:%M:%S')})
        event(state, 'SNIPER', f'{symbol}: simulated ${allocation:,.2f} entry', stamp)
        event(state, 'EXIT', f'{symbol}: simulated close • net ${pnl:+.2f}', stamp)
        event(state, 'JOURNAL', f'{symbol}: closed round trip recorded, fees ${fee:.2f}', stamp)
    state['scanned'] += len(rows)
    state['scanner'].extend(rows)
    # A strict sequence axis avoids overlapping timestamps on rapid button clicks.
    state['equity'].append({'Cycle': n, 'Equity ($)': state['balance'], 'Time': stamp.isoformat()})
    event(state, 'CHIEF', f'Cycle {n:03d} complete • 6 scanned / 2 blocked / 2 paper closes', stamp)
    state['last'] = stamp.strftime('%H:%M:%S')

if 'terminal' not in st.session_state:
    st.session_state.terminal = {'cycle': 0, 'balance': INITIAL, 'scanned': 0, 'blocked': 0,
        'trades': [], 'scanner': [], 'activity': [], 'last': '—',
        'equity': [{'Cycle': 0, 'Equity ($)': INITIAL, 'Time': now().isoformat()}]}
    for _ in range(5):
        cycle(st.session_state.terminal)
s = st.session_state.terminal

st.markdown('''<style>
:root{color-scheme:dark} .stApp{background:#080d17;color:#dbe4f2}
[data-testid="stHeader"]{background:transparent} .block-container{padding-top:2rem;padding-bottom:2rem;max-width:1600px}
[data-testid="stSidebar"]{background:#0c1322;border-right:1px solid #202b40}
h1,h2,h3{letter-spacing:-.035em} h1{font-size:2rem!important} h3{font-size:1.1rem!important}
p, label{color:#aebbd0} .brand{font-weight:800;font-size:24px;letter-spacing:-1px;color:#f0f5ff}
.sub{font-size:11px;color:#7c8da8;letter-spacing:2px;text-transform:uppercase}
.badge{display:inline-block;padding:6px 10px;border:1px solid #225a50;border-radius:5px;background:#102b29;color:#58e3ba;font:600 11px monospace;letter-spacing:1px}
.agent{background:linear-gradient(135deg,#111d30,#0e1626);border:1px solid #24314a;border-radius:9px;padding:14px 15px;margin-bottom:10px;min-height:105px}
.agent-name{font:700 13px monospace;color:#e3ebfa}.dot{color:#60ddc1;float:right}.role{font-size:11px;color:#8d9db6;margin-top:9px}.state{font:10px monospace;color:#a998ff;margin-top:8px}
[data-testid="stMetric"]{border:1px solid #233049;border-radius:10px;background:#0e1728;padding:16px}
[data-testid="stMetricValue"]{font-family:monospace;font-size:27px;color:#ecf5ff}
[data-testid="stMetricLabel"]{font-size:12px;color:#92a5c1}
.stButton>button{border:1px solid #41c9aa!important;background:#133c36!important;color:#80f2ce!important;font-weight:700;border-radius:7px}
[data-testid="stDataFrame"]{border:1px solid #233049;border-radius:8px}
hr{border-color:#1c2940!important} .foot{font:11px monospace;color:#6f819b;margin-top:20px}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">◈ PumpGrok</div><div class="sub">Research desk / terminal</div>', unsafe_allow_html=True)
    st.write('')
    st.markdown('<span class="badge">● PAPER SIMULATION</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown('### Workspace')
    st.markdown('**◉  Terminal overview**  \n\n◈  Synthetic scanner  \n\n▤  Paper ledger  \n\n◎  Agent telemetry')
    st.divider()
    st.caption('ENGINE CONFIGURATION')
    st.write('Initial demo equity: **$10,000**')
    st.write('Open exposure: **$0**')
    st.write('Fill model: **instant round trip**')
    st.write('Illustrative fees: **0.20%**')
    st.divider()
    st.caption('ISOLATION GUARANTEE')
    st.caption('No network data. No wallets. No keys. No real orders. No actual agent connections. The real desk hold is unchanged.')

left, right = st.columns([3, 1])
with left:
    st.markdown('<div class="sub">PUMPGROK / DESK 01 / DEMO</div>', unsafe_allow_html=True)
    st.title('Trading terminal')
    st.caption('Synthetic markets. Simulated agents. One controlled cycle at a time.')
with right:
    st.markdown('<span class="badge">● PAPER ONLY · DEMO</span>', unsafe_allow_html=True)
    if st.button('Run Scanner Cycle', type='primary', width='stretch'):
        cycle(s)
    st.caption(f'Cycle {s["cycle"]:03d} · last run {s["last"]} UTC+6')

st.info('ISOLATED DEMO — five illustrative cycles are preloaded. Every value, agent status and feed entry is simulated; this does not operate the PumpGrok desk.')
pnl = round(s['balance'] - INITIAL, 2)
cols = st.columns(4)
cols[0].metric('PAPER BALANCE', f'${s["balance"]:,.2f}', 'No open positions', delta_color='off')
cols[1].metric('NET PAPER P&L', f'${pnl:+,.2f}', f'{pnl/INITIAL:.2%} from demo inception')
cols[2].metric('SIMULATED PAIRS SCANNED', f'{s["scanned"]:,}', f'{s["cycle"]} demo cycles', delta_color='off')
cols[3].metric('SYNTHETIC RUGS BLOCKED', f'{s["blocked"]:,}', '2 per demo cycle', delta_color='off')

st.markdown('### Agent mesh')
st.caption('10 / 10 simulated seats · display-only status, not real agent health')
for row in [list(ROLES.items())[:5], list(ROLES.items())[5:]]:
    for col, (name, role) in zip(st.columns(5), row):
        col.markdown(f'<div class="agent"><div class="agent-name">{name}<span class="dot">●</span></div><div class="role">{role}</div><div class="state">DEMO · CYCLE {s["cycle"]:03d} COMPLETE</div></div>', unsafe_allow_html=True)

chart_col, feed_col = st.columns([1.25, 1])
with chart_col:
    st.markdown('### Equity trajectory')
    st.caption('Realized synthetic equity · USD · net of illustrative fees')
    eq = pd.DataFrame(s['equity'])
    fig = go.Figure(go.Scatter(x=eq['Cycle'], y=eq['Equity ($)'], customdata=eq['Time'], mode='lines+markers',
        line=dict(color='#58dfbc', width=3), marker=dict(size=5), fill='tozeroy', fillcolor='rgba(66,218,176,.08)',
        hovertemplate='Demo cycle %{x}<br>Equity $%{y:,.2f}<br>%{customdata}<extra></extra>'))
    low, high = eq['Equity ($)'].min(), eq['Equity ($)'].max()
    pad = max((high-low)*.3, 20)
    fig.update_layout(height=310, margin=dict(l=10,r=15,t=15,b=20), paper_bgcolor='#0e1728', plot_bgcolor='#0e1728',
        font=dict(color='#8fa1bc'), showlegend=False, xaxis=dict(title='Simulated cycle',dtick=max(1,s['cycle']//8),gridcolor='#1d2a40'),
        yaxis=dict(title='Equity (USD)',tickprefix='$',range=[low-pad,high+pad],gridcolor='#1d2a40'))
    st.plotly_chart(fig, width='stretch', config={'displayModeBar':False})
with feed_col:
    st.markdown('### Live scanner feed · DEMO')
    st.caption('Updates only on simulated cycles · no live market connection')
    st.dataframe(pd.DataFrame(s['scanner'][::-1]).drop(columns=['Cycle','Time (UTC+6)']), hide_index=True, height=310, width='stretch',
        column_config={'Synthetic price ($)':st.column_config.NumberColumn(format='$%.6f'), 'Score':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%d')})

trades_tab, logs_tab = st.tabs(['▤  Paper trade ledger', '◎  Simulated agent activity'])
with trades_tab:
    st.caption(f'{len(s["trades"])} synthetic round trips · every position closed · balances reflect net P&L including fees')
    st.dataframe(pd.DataFrame(s['trades'][::-1]), hide_index=True, width='stretch', height=300,
        column_config={k:st.column_config.NumberColumn(format='$%.2f') for k in ['Notional ($)','Fees ($)','Net P&L ($)']})
with logs_tab:
    agent = st.selectbox('Filter simulated agent', ['All agents'] + list(ROLES))
    logs = [v for v in reversed(s['activity']) if agent == 'All agents' or v['Agent']==agent]
    st.dataframe(pd.DataFrame(logs[:300]), hide_index=True, width='stretch', height=330)
st.markdown('<div class="foot">PUMPGROK / SANDBOX ONLY · Session-local state resets on a new session or server restart · All timestamps Asia/Dhaka (UTC+6)</div>', unsafe_allow_html=True)
