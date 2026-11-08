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

# Reference-led, light monospaced terminal. The synthetic engine above is unchanged.
from html import escape

st.markdown('''<style>
:root{color-scheme:light!important}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:#fafafa!important;color:#292d34!important;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace!important}
[data-testid="stHeader"]{background:transparent;height:1.6rem}
.block-container{max-width:1280px;padding:2rem 2rem 1.5rem}
[data-testid="stVerticalBlock"]{gap:.65rem}
p,span,label,input,button,[data-testid="stCaptionContainer"]{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace!important}
p{font-size:12px;color:#5c626c} [data-testid="stCaptionContainer"]{font-size:10px;color:#92969e}
[data-testid="stHorizontalBlock"]{gap:1.25rem}
.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px dashed #d7d9df;padding:0 0 20px;margin-bottom:4px;gap:12px}
.identity{display:flex;align-items:center;gap:17px}.pause{width:48px;height:48px;background:#eceef1;border-radius:50%;display:grid;place-items:center;color:#a3a7af;font-size:19px;letter-spacing:4px;padding-left:4px;flex-shrink:0}
.brand{font-size:20px;font-weight:750;letter-spacing:-1px;color:#242731}.brand b{color:#437bdf}.meta{font-size:10px;color:#9296a0;margin-top:9px;line-height:1.8}.running{color:#359f6b}.badge{padding:3px 5px;border-radius:3px;font-size:8px;letter-spacing:.5px;background:#e8eaf9;color:#8580b8;margin-left:6px}.paper{background:#e9f5e9;color:#6a9874}
.balance{text-align:right;font-size:27px;letter-spacing:-1.2px;font-weight:700}.balance small{font-size:9px;color:#999ea7;display:block;font-weight:400;letter-spacing:1px;margin-bottom:5px}.stats{font-size:10px;color:#969aa3;margin-top:8px;letter-spacing:0;font-weight:400}.green{color:#36aa79!important}.pink{color:#d47995!important}.blue{color:#5e8cd7!important}.purple{color:#a08bc4!important}.amber{color:#c6a257!important}
.kicker{font-size:9px;letter-spacing:1.8px;color:#9c9fa7;text-transform:uppercase;margin:4px 0 11px}.rail{display:flex;flex-direction:column;gap:9px}.seat{display:flex;align-items:center;gap:11px;background:#fff;border:1px solid #e7e8eb;border-radius:10px;padding:12px 11px;min-height:67px}.seat.active{background:#f0f9f4;border-color:#b6dfc8}.icon{background:var(--tint);color:var(--accent);width:32px;height:32px;display:grid;place-items:center;border-radius:7px;font-size:17px;flex-shrink:0}.active .icon{border:1px solid #74c99c;border-radius:50%;background:#e7f7ed}.seat-name{font-size:10px;font-weight:700;letter-spacing:.6px;color:var(--accent)}.seat-sub{font-size:9px;color:#9a9da5;margin-top:5px}.pill{font-size:7px;color:#9b9ea5;background:#f4f4f6;border-radius:4px;padding:3px 4px;margin-left:auto;align-self:flex-start;white-space:nowrap}.rail-foot{border-top:1px dashed #d9dbe0;padding:13px 3px;margin-top:14px;color:#999da4;font-size:9px;line-height:1.8}
.film{border:1px solid #e4e6ea;border-radius:10px;background-color:#fdfdfd;background-image:radial-gradient(#e1e5eb .75px,transparent .75px);background-size:13px 13px;padding:16px 17px 14px;overflow:hidden}.film-head{display:flex;justify-content:space-between;font-size:9px;letter-spacing:1.4px;color:#9297a2;margin-bottom:14px}.film-head strong{color:#6e9d7c;font-weight:400}.stage-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.stage{font-size:8px;color:#9599a1;letter-spacing:1px;min-width:0}.stage-card{background:#fff;border:1px solid #e2e5e9;border-radius:6px;padding:10px 7px;margin-top:7px;font-size:10px;color:#515963;letter-spacing:0;min-height:59px;overflow:hidden}.stage-card span{display:block;margin-top:7px;font-size:8px;color:#9a9fa7}.stage-card.good{border-color:#b7ddc7;background:#f0faf3}.stage-card.bad{border-color:#f0d6df;background:#fdf5f7}.wire{display:flex;justify-content:space-between;align-items:center;margin-top:13px;border-top:1px dashed #e1e5e8;padding-top:10px;font-size:9px;color:#9097a0}.executor{border:1px solid #7ec99f;background:#e8f6ed;color:#5ca579;border-radius:50%;width:29px;height:29px;display:grid;place-items:center;font-size:16px}.wire .trace{flex:1;border-top:1px dashed #c5dace;margin:0 9px}
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;border-bottom:1px dashed #d9dce2;padding:15px 0 17px}.summary .lbl{font-size:8px;letter-spacing:1px;color:#949aa3}.summary .val{font-size:19px;color:#3e4650;margin-top:7px;letter-spacing:-.7px}.summary .note{font-size:8px;color:#a2a6ae;margin-top:5px}.dot{display:inline-block;width:5px;height:5px;border-radius:50%;margin-right:5px;background:var(--accent)}
.trade{border:1px solid #e3e7e6;border-radius:8px;background:#fff;padding:16px;margin-top:0}.trade-top{display:flex;justify-content:space-between;align-items:center}.token{font-size:18px;font-weight:700;letter-spacing:-.7px;color:#424850}.gain{font-size:22px;font-weight:600;letter-spacing:-1px}.trade-sub{font-size:9px;color:#9a9fa7;margin:7px 0 14px}.details{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px}.detail{font-size:9px;color:#9a9fa7}.detail b{display:block;color:#606773;font-weight:400;margin-top:4px}.route{background:#f2f8f4;border:1px solid #e0ede5;border-radius:8px;padding:16px;height:100%;font-size:9px;color:#80a28d}.route-title{font-size:9px;color:#739480;letter-spacing:1px;margin-bottom:17px}.route-line{display:flex;justify-content:space-between;gap:10px;margin:12px 0}.route-line span:last-child{color:#529877}.route-end{text-align:right;border-top:1px dashed #d4e4d9;padding-top:12px;color:#54a476}.result{display:flex;justify-content:space-between;border-bottom:1px dashed #dadddf;padding:13px 0;color:#9a9ea6;font-size:9px}.result b{color:#59636b;font-weight:500}.section-head{display:flex;justify-content:space-between;color:#7e858f;font-size:9px;letter-spacing:1px;padding:11px 0 4px}.console-row{display:grid;grid-template-columns:58px 64px 1fr auto;gap:9px;align-items:center;border-bottom:1px solid #edefef;padding:10px 0;font-size:9px;color:#858c96}.console-time{color:#a0a5ad}.tag{background:var(--tint);color:var(--accent);font-size:8px;padding:4px 5px;border-radius:3px;display:inline-block;text-align:center}.console-result{color:#76a38b;font-size:8px}.console-message{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.footer{font-size:8px;line-height:1.9;color:#a0a5ad;border-top:1px dashed #dddfe4;padding-top:12px;margin-top:15px}
.stButton>button{background:#edf6f0!important;border:1px solid #c2dacb!important;color:#53876a!important;border-radius:6px!important;min-height:33px!important;padding:3px 14px!important;box-shadow:none!important}.stButton>button p{font-size:10px!important;color:#53876a!important}.stButton>button:hover{background:#dff0e5!important;border-color:#90bea2!important}
[data-baseweb="tab-list"]{gap:22px;border-bottom:1px dashed #dcdee3}[data-baseweb="tab"]{font-size:10px!important;color:#858c97!important;background:transparent!important;height:36px}[aria-selected="true"]{color:#527caa!important}[data-baseweb="tab-highlight"]{background:#8aaacb!important;height:1px!important}
[data-testid="stDataFrame"]{border:1px solid #e7e9ec;border-radius:7px}[data-testid="stSelectbox"] label p{font-size:9px!important}[data-baseweb="select"]>div{background:#fff!important;color:#747d88!important;border-color:#e2e5e9!important;font-size:10px!important}[data-testid="stExpander"]{border-color:#e2e5e9!important;background:#fff}
@media(max-width:760px){.block-container{padding:1.7rem 1rem}.top{align-items:flex-start}.identity{gap:9px}.pause{width:34px;height:34px;font-size:14px}.brand{font-size:16px}.balance{font-size:21px}.meta{font-size:8px}.stats{font-size:8px}.stage-strip{gap:5px}.stage-card{font-size:8px;padding:8px 4px}.summary{gap:7px}.summary .val{font-size:16px}.summary .lbl{font-size:7px}.console-row{grid-template-columns:45px 55px 1fr;gap:5px}.console-result{display:none}.rail{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.seat{padding:9px 7px;gap:7px;min-height:62px}.seat-name{font-size:9px}.pill{display:none}.rail-foot{display:none}.icon{width:26px;height:26px}.seat-sub{font-size:8px}}
</style>''', unsafe_allow_html=True)

# Callback runs before drawing, keeping every displayed value in sync.
st.session_state.setdefault('terminal', s)
PALETTE = {
 'CHIEF':('#8c9aa7','#edf0f4','⌘','ORCHESTRATOR'),
 'SCOUT':('#c5a15b','#fbf3df','⌕','SCANNER'),
 'RISK':('#ce91a5','#fbeef2','◇','RUG CHECK'),
 'WHALE':('#a390c6','#f1edf9','◉','HOLDER CHECK'),
 'SNIPER':('#69ac84','#e8f5ed','↗','EXECUTOR'),
 'RUG':('#cf8ba3','#fbeef2','△','THREAT WATCH'),
 'EXIT':('#8db3a0','#eef6f0','↳','PAPER EXIT'),
 'SHILL':('#c6a263','#faf3e5','≋','NARRATIVE'),
 'SIGNAL':('#9e8ac0','#f1edf8','⌁','SIZER / SIGNAL'),
 'JOURNAL':('#c5a15e','#faf2df','▤','LOGGER / EQUITY')}

def html(value):
    st.markdown(value, unsafe_allow_html=True)

def chart():
    eq = pd.DataFrame(s['equity'])
    low, high = eq['Equity ($)'].min(), eq['Equity ($)'].max()
    pad = max((high-low)*.3, 15)
    fig = go.Figure(go.Scatter(x=eq['Cycle'],y=eq['Equity ($)'],customdata=eq['Time'],
        mode='lines+markers',line=dict(color='#80bd98',width=2),marker=dict(size=4),
        hovertemplate='DEMO cycle %{x}<br>Equity $%{y:,.2f}<br>%{customdata}<extra></extra>'))
    fig.update_layout(height=165,margin=dict(l=8,r=8,t=9,b=20),paper_bgcolor='#fafafa',plot_bgcolor='#fafafa',
        font=dict(family='monospace',size=9,color='#9aa1aa'),showlegend=False,
        xaxis=dict(title=None,dtick=max(1,s['cycle']//8),gridcolor='#eceef1',zeroline=False),
        yaxis=dict(title=None,tickprefix='$',range=[low-pad,high+pad],gridcolor='#eceef1',zeroline=False))
    st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})

# Put the native trigger first in execution; position it below the compact header.
pnl = round(s['balance']-INITIAL,2)
wins = sum(t['Net P&L ($)']>0 for t in s['trades'])
losses = sum(t['Net P&L ($)']<0 for t in s['trades'])
html(f'''<div class="top"><div class="identity"><div class="pause" aria-label="Decorative pause mark">Ⅱ</div><div><div class="brand"><b>Grok Bot</b> Terminal</div><div class="meta"><span class="running">● Running demo</span> · {now().strftime('%H:%M:%S')} UTC+6 <span class="badge">SIMULATED</span><span class="badge paper">PAPER</span></div></div></div><div class="balance"><small>PAPER BALANCE / USD</small>${s['balance']:,.2f}<div class="stats">{len(s['trades'])} trades · <span class="green">{wins} wins</span> · <span class="pink">{losses} losses</span></div></div></div>''')
control, context = st.columns([1,2.6])
with control:
    st.button('Run Scanner Cycle',on_click=cycle,args=(s,),width='stretch')
with context:
    st.caption(f'PUMPGROK / CYCLE {s["cycle"]:03d} · Manual synthetic cycles only · No real agent or market connections')
rail, body = st.columns([1,3],gap='large')
with rail:
    html('<div class="kicker">Desk agents / all simulated</div>')
    cards=[]
    for name in ROLES:
        accent,tint,icon,subtitle=PALETTE[name]
        cards.append(f'<div class="seat {"active" if name=="SNIPER" else ""}" style="--accent:{accent};--tint:{tint}"><div class="icon">{icon}</div><div><div class="seat-name">{name}</div><div class="seat-sub">{subtitle}</div></div><span class="pill">DEMO</span></div>')
    html('<div class="rail">'+''.join(cards)+'</div><div class="rail-foot">10 / 10 demo seats<br>● CYCLE COMPLETE<br>Real desk hold unchanged<br>No keys · No wallets · No orders</div>')
with body:
    latest=s['trades'][-1]
    recent=s['scanner'][-6:]
    blocked=next(r for r in recent if r['Decision']=='BLOCKED')
    stages=[('SCAN',recent[0]['Demo pair'],'6 synthetic pairs',''),('CHECK',blocked['Demo pair'],'△ risk blocked','bad'),('SIZE',latest['Demo pair'],f"${latest['Notional ($)']:.0f} demo size",''),('EXEC',latest['Demo pair'],'↗ paper closed','good'),('LOG',latest['ID'],'ledger reconciled','')]
    stage_html=''.join(f'<div class="stage">{name}<div class="stage-card {cls}">{token}<span>{text}</span></div></div>' for name,token,text,cls in stages)
    html(f'<div class="film"><div class="film-head"><span>● LIVE FILM / SIMULATED PIPELINE</span><strong>CYCLE {s["cycle"]:03d}</strong></div><div class="stage-strip">{stage_html}</div><div class="wire"><span class="pink">△ {s["blocked"]} synthetic threats blocked</span><span class="trace"></span><span class="executor">↗</span><span class="trace"></span><span class="green">PAPER EXECUTOR</span></div></div>')
    html('<div class="section-head"><span>BLUE EQUITY / REALIZED PAPER CURVE</span><span>USD · NET OF DEMO FEES</span></div>')
    chart()
    blocks=[('FILTER / PAIRS',str(s['scanned']),'synthetic pairs scanned','#c8aa69'),('MIXER / BLOCKS',str(s['blocked']),'hypothetical rugs blocked','#cf90a7'),('LOGGER / FILLS',str(len(s['trades'])),'closed paper round trips','#aaa0c9'),('ROUTER / NET P&L',f'${pnl:+,.2f}','0.20% illustrative fees','#80b999')]
    html('<div class="summary">'+''.join(f'<div><div class="lbl"><span class="dot" style="--accent:{color}"></span>{label}</div><div class="val {"green" if idx==3 and pnl>=0 else ""}">{value}</div><div class="note">{note}</div></div>' for idx,(label,value,note,color) in enumerate(blocks))+'</div>')
    html('<div class="section-head"><span>LATEST PAPER TRADE</span><span>CLOSED / NO OPEN EXPOSURE</span></div>')
    trade_col, route_col=st.columns([1.35,1])
    net=latest['Net P&L ($)']
    with trade_col:
        html(f'''<div class="trade"><div class="trade-top"><span class="token">{latest['Demo pair']}</span><span class="gain {'green' if net>=0 else 'pink'}">${net:+.2f}</span></div><div class="trade-sub">{latest['ID']} · synthetic round trip · {latest['Time (UTC+6)']} UTC+6</div><div class="details"><div class="detail">ENTRY<b>${latest['Entry ($)']:.6f}</b></div><div class="detail">EXIT<b>${latest['Exit ($)']:.6f}</b></div><div class="detail">PAPER SIZE<b>${latest['Notional ($)']:.2f}</b></div><div class="detail">FEES / NET RETURN<b>${latest['Fees ($)']:.2f} / {net/latest['Notional ($)']:+.2%}</b></div><div class="detail">REASON<b>Demo threshold passed</b></div><div class="detail">EXECUTION<b>Instant synthetic close</b></div></div></div>''')
    with route_col:
        html(f'''<div class="route"><div class="route-title">↗ SIMULATED EXECUTION ROUTE</div><div class="route-line"><span>RISK → SIGNAL</span><span>DEMO CLEAR ✓</span></div><div class="route-line"><span>SIGNAL → SNIPER</span><span>SIZE ${latest['Notional ($)']:.0f}</span></div><div class="route-line"><span>SNIPER → EXIT</span><span>PAPER CLOSED ✓</span></div><div class="route-line"><span>EXIT → JOURNAL</span><span>RECONCILED ✓</span></div><div class="route-end">NO BROADCAST · NO NETWORK</div></div>''')
    html(f'<div class="result"><span>START <b>${INITIAL:,.2f}</b></span><span>END <b>${s["balance"]:,.2f}</b></span><span class="{"green" if pnl>=0 else "pink"}">NET ${pnl:+,.2f}</span></div>')
    html('<div class="section-head"><span>TERMINAL / LATEST CYCLE</span><span>CHRONOLOGICAL · UTC+6</span></div>')
    # One line per seat from the latest cycle, sorted in actual execution order.
    cycle_events=s['activity'][-50:]
    seen=set(); selected=[]
    for entry in reversed(cycle_events):
        if entry['Agent'] not in seen:
            seen.add(entry['Agent']);selected.append(entry)
    rows=[]
    for entry in reversed(selected):
        name=entry['Agent']; accent,tint,_,_=PALETTE[name]
        message=escape(entry['Simulated activity'])
        result='BLOCK' if name=='RUG' else ('CLOSED' if name in ('EXIT','SNIPER') else 'DEMO')
        rows.append(f'<div class="console-row"><span class="console-time">{entry["Time (UTC+6)"]}</span><span class="tag" style="--accent:{accent};--tint:{tint}">{name}</span><span class="console-message" title="{message}">{message}</span><span class="console-result">{result}</span></div>')
    html(''.join(rows))

st.caption('ISOLATED PAPER DEMO · Five example cycles preloaded. The feed advances only when you run a cycle. No real market data or trading capabilities.')
scanner_tab, trades_tab, logs_tab=st.tabs(['Live scanner · simulated','Paper trade log','Agent activity logs'])
# Explicit light dataframe styling keeps tables legible even if host prefers dark.
def table(frame,height=260,config=None):
    styled=frame.style.set_properties(**{'background-color':'#ffffff','color':'#65707c','font-family':'monospace','font-size':'11px'})
    st.dataframe(styled,hide_index=True,width='stretch',height=height,column_config=config)
with scanner_tab:
    table(pd.DataFrame(s['scanner'][::-1]),config={'Synthetic price ($)':st.column_config.NumberColumn(format='$%.6f')})
with trades_tab:
    table(pd.DataFrame(s['trades'][::-1]),config={k:st.column_config.NumberColumn(format='$%.2f') for k in ['Notional ($)','Fees ($)','Net P&L ($)']})
with logs_tab:
    agent=st.selectbox('Filter simulated agent',['All agents']+list(ROLES))
    logs=[v for v in reversed(s['activity']) if agent=='All agents' or v['Agent']==agent]
    table(pd.DataFrame(logs[:300]))
html('<div class="footer">PUMPGROK / GROK BOT TERMINAL · SIMULATED PAPER SANDBOX ONLY<br>Balances and logs are browser-session local, not persisted. New sessions or server restarts reset the demo. All times Asia/Dhaka (UTC+6).</div>')
