"""English dark real-market research terminal. Execution remains fail-closed."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import os
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from market_paper_terminal.core import Store,scan,age,audit,gate,halt_status,ROLES,FRESH_SECONDS,DOCS

st.set_page_config(page_title='PumpGrok | Market Scanner v2',page_icon='◈',layout='wide')
BASE=Path(__file__).parent
store=Store(Path(os.environ.get('PUMPGROK_TERMINAL_DB',str(BASE/'market_paper_terminal/data/terminal.sqlite3'))))
TZ=ZoneInfo('Asia/Dhaka')
LOCALIZED=re.compile('[\u0980-\u09ff]')
def english(value):
 """Presentation only: do not alter historical evidence in the database."""
 if isinstance(value,str) and LOCALIZED.search(value):return 'Localized source text hidden; original preserved in database.'
 if isinstance(value,dict):return {english(k):english(v) for k,v in value.items()}
 if isinstance(value,list):return [english(v) for v in value]
 return value
def local(stamp):
 try:return datetime.fromisoformat(stamp).astimezone(TZ).strftime('%d %b %H:%M:%S UTC+6')
 except (ValueError,TypeError):return 'Unknown'
def html(value):st.markdown(value,unsafe_allow_html=True)
def table(frame):
 if frame.empty:st.caption('No records yet.');return
 frame=frame.map(english)
 styled=frame.style.set_properties(**{'background-color':'#111c2e','color':'#d2deee','border-color':'#25354c','font-size':'13px'})
 st.dataframe(styled,hide_index=True,width='stretch',height=min(390,72+len(frame)*36))
def legacy_message(event):
 text=event['message']
 if not LOCALIZED.search(text):return text
 summaries={'CODE / DISCOVERY':'Read public discovery profiles.','CODE / MARKET':'Read exact-mint public pair data.',
 'CODE / EVIDENCE':'Validated market observations; mandatory safety audit remains BLIND.',
 'CODE / JOURNAL':'Saved observations and provenance; no orders placed.'}
 return summaries.get(event['stage'],'Historical code event.')+' [Legacy localized log; original retained.]'

st.markdown('''<style>
:root{color-scheme:dark!important;--background-color:#070b14;--secondary-background-color:#111c2e;--text-color:#d9e5f5;--primary-color:#45d9b3}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:#070b14!important;color:#d9e5f5!important}
.block-container{max-width:1440px;padding:2rem 2rem 1.5rem}[data-testid="stHeader"]{background:rgba(7,11,20,.9)}
p,span,label,button,input{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif!important}p{font-size:14px;color:#a7b8d0;line-height:1.65}h1,h2,h3{color:#e7effb!important;letter-spacing:-.03em}h3{font-size:18px!important}
.header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #223049;padding:0 0 19px;margin-bottom:14px;gap:16px}.brand{font:700 24px ui-monospace,Consolas,monospace;letter-spacing:-1px;color:#edf5ff}.brand b{color:#5bdddb}.brand-icon{color:#49dab0;margin-right:10px}.version{font:11px ui-monospace,monospace;color:#8095b4;margin-top:9px;letter-spacing:.4px}.chips{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.chip{padding:6px 9px;border:1px solid #28594f;border-radius:5px;background:#0d2926;color:#5cdbb5;font:600 10px monospace;letter-spacing:.7px}.chip.cyan{background:#0e2431;border-color:#215065;color:#70d7ed}.chip.amber{background:#2d2518;border-color:#59472a;color:#e1bd7a}
.safety{background:#211d16;border:1px solid #4a3b29;border-radius:8px;padding:12px 16px;display:flex;gap:13px;align-items:flex-start;color:#c6b690;font-size:13px;line-height:1.6;margin-bottom:13px}.safety strong{color:#e8c180;white-space:nowrap;font:600 11px monospace;padding-top:3px}.safety span{color:#c9bb9f}.state{background:linear-gradient(110deg,#0f2130,#101a2a);border:1px solid #284458;border-left:3px solid #47c9c8;border-radius:9px;padding:18px 20px;margin:7px 0}.state-head{display:flex;justify-content:space-between;gap:10px}.eyebrow{font:10px monospace;letter-spacing:1.7px;color:#7f9ab7}.state h2{font-size:22px;margin:8px 0;color:#dcebf9}.state p{margin:6px 0;font-size:14px;color:#a9bdd2}.state .next{font-size:12px;color:#70bdb1;border-top:1px solid #253a4b;padding-top:11px;margin-top:12px}.idle{color:#94abc2;font:11px monospace}.working{color:#6de1ce;font:11px monospace}
[data-testid="stMetric"]{background:linear-gradient(130deg,#111c2e,#0e1727);border:1px solid #24334a;border-radius:9px;padding:14px 16px}[data-testid="stMetricValue"]{font:25px ui-monospace,monospace;color:#e4effd}[data-testid="stMetricLabel"] p{color:#90a6c1;font-size:11px;font-weight:500}[data-testid="stHorizontalBlock"]{gap:1.1rem}.section{font:600 11px monospace;letter-spacing:1.2px;color:#899db8;margin:16px 0 11px}.seat{background:#0e1727;border:1px solid #223149;border-radius:8px;padding:12px 13px;margin-bottom:8px}.seat b{font:600 12px monospace;color:#b7b2e0}.seat span{font:8px monospace;color:#8a9bb4;background:#1b2638;padding:4px 5px;border-radius:4px;float:right}.seat p{font-size:11px;color:#91a3be;margin:7px 0 0;line-height:1.5}.seat-note{font-size:11px;color:#7f92ac;line-height:1.8;border-top:1px solid #26364b;padding-top:14px;margin-top:14px}.health{background:#0e1827;border:1px solid #26364a;border-radius:8px;padding:13px 16px;margin-bottom:10px}.health-title{font:11px monospace;color:#7fbeb2;letter-spacing:.8px}.health-time{font:11px monospace;color:#879bb6;margin-top:8px}.foot{font:11px monospace;color:#7186a3;border-top:1px solid #243149;padding-top:15px;margin-top:20px;line-height:1.9}
.stButton>button,[data-testid="stFormSubmitButton"]>button{background:#123b35!important;border:1px solid #338a77!important;color:#91f3d1!important;border-radius:6px!important;min-height:39px!important;box-shadow:0 0 16px #25bc8d0c}.stButton>button p,[data-testid="stFormSubmitButton"]>button p{color:#91f3d1!important;font-size:13px!important;font-weight:600}.stButton>button:hover{background:#195044!important;border-color:#54c8a8!important}.stLinkButton>a{background:#10232e!important;color:#82d5e9!important;border:1px solid #2b4e60!important;font-size:12px!important}
[data-baseweb="select"]>div,[data-baseweb="input"],[data-baseweb="input"]>input,[data-testid="stNumberInputContainer"]{background:#111d30!important;color:#dae6f7!important;border-color:#30435f!important}input{color:#dbe8f8!important}[data-testid="stNumberInput"] button{background:#1b2a40!important;color:#c8d8ed!important}[data-baseweb="popover"],[data-baseweb="popover"] ul,[data-baseweb="menu"]{background:#142137!important;color:#d5e4f5!important}[role="option"]{background:#142137!important;color:#d5e4f5!important}[role="option"]:hover{background:#203651!important}
[data-baseweb="tab-list"]{gap:25px;border-bottom:1px solid #26334b}[data-baseweb="tab"]{background:transparent!important;color:#8ea6c4!important;font-size:12px!important}[data-baseweb="tab"][aria-selected="true"]{color:#66d5c3!important}[data-baseweb="tab-highlight"]{background:#42bfa9!important;height:2px!important}
[data-testid="stDataFrame"]{border:1px solid #293b53;border-radius:8px;--gdg-bg-cell:#111c2e;--gdg-bg-header:#18273c;--gdg-text-dark:#d7e4f5;--gdg-text-medium:#a3bad3;--gdg-border-color:#263950;--gdg-accent-color:#3bcda7}
[data-testid="stJson"],[data-testid="stJson"]>div,[data-testid="stCode"]{background:#101b2b!important;color:#bfd1e7!important;border-color:#293a51!important}[data-testid="stExpander"],[data-testid="stForm"]{background:#0d1625!important;border-color:#273950!important;border-radius:8px}[data-testid="stExpander"] details summary p{color:#b8cce3!important}[data-testid="stCaptionContainer"] p{color:#7d94b2;font-size:12px;line-height:1.7}[data-testid="stAlert"]{background:#142238!important;border:1px solid #2b405b!important;color:#c3d6ee!important;border-radius:7px}[data-testid="stAlert"] p{color:#c3d6ee!important}[data-testid="stStatusWidget"]{background:#101e2e!important;border-color:#2b475a!important;color:#bcd4e9!important}[data-testid="stToast"]{background:#18293d!important;color:#c4dfec!important}
@media(max-width:760px){.block-container{padding:1.6rem .8rem}.header{align-items:flex-start;flex-direction:column;gap:12px}.brand{font-size:21px}.chips{justify-content:flex-start}.state{padding:15px}.state h2{font-size:20px}.safety{flex-direction:column;gap:6px}[data-testid="stMetricValue"]{font-size:22px}.version{font-size:10px}}
</style>''',unsafe_allow_html=True)

html('<div class="header"><div><div class="brand"><span class="brand-icon">◈</span><b>PumpGrok</b> Terminal</div><div class="version">Market Scanner v2 • English / Dark</div></div><div class="chips"><span class="chip cyan">REAL MARKET DATA</span><span class="chip">PAPER ONLY</span><span class="chip amber">EXECUTION LOCKED</span></div></div>')
halt=halt_status()
html('<div class="safety"><strong>EXECUTION LOCKED</strong><span>'+escape(halt)+'. Desk engine not connected; effective configuration unverified. All paper buys and sells remain locked. No wallets or live orders.</span></div>')
current=st.empty()
current.markdown('<div class="state"><div class="state-head"><span class="eyebrow">CURRENT ACTIVITY / RESEARCH SCANNER</span><span class="idle">● IDLE</span></div><h2>Ready for a read-only market scan</h2><p>No scan is running. Start a cycle to fetch real public profiles and exact-mint pair data, validate the response, and save source evidence.</p><div class="next">Next: code discovery → market data → evidence checks → storage. This is not activity from the ten assistant Bots.</div></div>',unsafe_allow_html=True)
if st.button('Run Scanner Cycle',type='primary'):
 with st.status('Reading public market data…',expanded=True) as status:
  def progress(stage,text):
   text=english(text)
   current.markdown(f'<div class="state"><div class="state-head"><span class="eyebrow">CURRENT ACTIVITY / {escape(stage)}</span><span class="working">● CODE RUNNING</span></div><h2>Read-only scanner cycle</h2><p>{escape(text)}</p><div class="next">Public API reads only. No assistant Bot or order execution has been started.</div></div>',unsafe_allow_html=True)
   st.write(f'**{stage}** — {text}')
  result=scan(store,progress=progress)
  health=store.get('health',{})
  status.update(label='Scan result: '+english(result['message']),state='error' if health.get('status') in ('ERROR','BLOCKED') else 'complete',expanded=True)
 st.session_state['scan_result']=result
 current.markdown('<div class="state"><div class="state-head"><span class="eyebrow">CURRENT ACTIVITY</span><span class="idle">● IDLE</span></div><h2>Request finished</h2><p>'+escape(english(result['message']))+'</p><div class="next">No fetch is running. No trade was placed.</div></div>',unsafe_allow_html=True)
if st.session_state.get('scan_result'):st.caption(english(st.session_state['scan_result']['message']))
st.caption('Manual cycles only · 30-second shared cooldown · Up to 8 discovered mints per batch · No scheduled polling or synthetic fallback')
rows=store.rows();health=store.get('health',{});cash=store.cash()
cols=st.columns(5)
for col,label,value in zip(cols,['Paper Cash / Equity','Realized / Unrealized P&L','Unique Pairs Observed','Confirmed Rugs Blocked','Open Paper Positions'],[f'${cash:.2f}','$0.00 / $0.00',len(rows),0,0]):col.metric(label,value)
st.caption('Paper capital: $50. No filled trades or completed on-chain audits. Missing evidence is BLIND, not proof of a rug.')
rail,body=st.columns([1,3],gap='large')
with rail:
 html('<div class="section">AGENT STATUS / 10 SEATS</div>')
 for role,description in ROLES.items():html(f'<div class="seat"><b>{role}</b><span>NOT CONNECTED</span><p>{escape(english(description))}</p></div>')
 html('<div class="seat-note">Scanner activity is executed by local code, not these assistants.<br>Risk, holder, social and execution integrations are incomplete.<br>No autonomy has been activated.</div>')
with body:
 html('<div class="section">DATA SOURCES / PROVIDER HEALTH</div>')
 health_status=health.get('status','NOT FETCHED')
 last=store.get('last_success')
 freshness='NOT FETCHED' if not last else ('STALE DATA' if age(last)>FRESH_SECONDS else 'RECENT RETRIEVAL')
 html(f'<div class="health"><div class="health-title">DEXSCREENER PUBLIC API · {escape(health_status)} · {freshness}</div><div class="health-time">Last successful retrieval: {local(last)}</div></div>')
 if health.get('error'):st.warning(english(health['error']))
 if store.get('provider_blocked'):st.warning('Provider access denied. Requests are stopped; no alternate route will be attempted. Owner/provider support is required.')
 st.caption('LIVE DATA SOURCE • Retrieval older than 60 seconds is STALE. The provider does not publish a price observation timestamp: retrieval age is not price age. Errors retain timestamped last-good data.')
 st.link_button('Official API Documentation',DOCS)
 st.subheader('Market Scanner')
 display=[]
 for r in rows:
  display.append({'Symbol (unverified)':english(r['symbol']),'Mint':r['mint'],'Pair':r['pair'],'Venue':english(r['venue']),
   'Indicative USD':r['price_usd'],'Liquidity USD':r['liquidity_usd'],'Volume 1h USD':r['volume_h1_usd'],
   'Retrieved':local(r['fetched_utc']),'Freshness':'STALE' if age(r['fetched_utc'])>FRESH_SECONDS else 'RECENT RETRIEVAL',
   'Price timestamp':'UNKNOWN','Source':r['url']})
 table(pd.DataFrame(display))
 st.caption('Discovery uses latest profiles, not the entire market or guaranteed new launches. Exact mint/pair addresses establish identity; symbols are unverified. Missing values are unavailable, never safe or zero. These prices are indicative marks, not executable quotes.')
 if rows:
  mint=st.selectbox('Select Exact Mint',sorted({r['mint'] for r in rows}))
  candidates=[r for r in rows if r['mint']==mint]
  selected=st.selectbox('Pair / Venue',list(range(len(candidates))),format_func=lambda i:candidates[i]['pair']+' / '+english(candidates[i]['venue']))
  row=candidates[selected]
  st.subheader('Safety Gates')
  evidence=audit(row)
  table(pd.DataFrame([{'Check':k,'Evidence':v} for k,v in evidence.items() if k not in ['mint','pair']]))
  with st.expander('Field-Level Provenance / Normalized Observation'):st.json(english(row))
  st.subheader('Research Ticket Preview')
  st.caption('Draft only. Exact manual approval and the core quote → simulate → place path are unavailable. This form cannot place orders.')
  with st.form('draft_ticket'):
   side=st.selectbox('Side',['BUY','SELL'])
   usd=st.number_input('Notional USD — maximum $2.50',min_value=0.01,max_value=2.50,value=2.50,step=0.01)
   slip=st.number_input('Maximum Slippage % — cap 3%',min_value=0.01,max_value=3.0,value=3.0,step=0.1)
   ticket={'mint':mint,'pair':row['pair'],'side':side,'usd':f'{usd:.2f}','slippage':f'{slip:.2f}'}
   st.json(ticket)
   save=st.form_submit_button('Save Research Draft — No Order')
  with st.expander('Execution Lock Details',expanded=False):
   for reason in gate(ticket,row,halt=halt):st.caption('🔒 '+english(reason))
  if save:
   tid=store.ticket(ticket);store.log('CODE / TICKET','Research draft saved; NOT approved; fills locked. ID '+tid[:12])
   st.success('Local research draft saved: '+tid[:12]+'. No order or fill was created.')
 else:st.caption('Run a real-data scan before creating an exact-mint research draft.')

curve_tab,trade_tab,log_tab,limits_tab=st.tabs(['Equity / Portfolio','Research Drafts','Activity Log','Safety / Integration'])
with curve_tab:
 st.write(f'Paper cash ${cash:.2f} · positions $0.00 · fees $0.00 · equity ${cash:.2f}')
 fig=go.Figure(go.Scatter(x=['Initial paper capital'],y=[cash],mode='markers',marker=dict(color='#57dfb5',size=10,line=dict(color='#a2ffe3',width=1)),hovertemplate='Paper cash $%{y:.2f}<extra></extra>'))
 fig.update_layout(template='plotly_dark',height=220,paper_bgcolor='#0e1727',plot_bgcolor='#0e1727',font=dict(family='monospace',color='#94abc7',size=11),yaxis=dict(title='Paper USD',range=[49,51],gridcolor='#213149',zeroline=False),xaxis=dict(gridcolor='#213149'),margin=dict(l=15,r=15,t=15,b=25),hoverlabel=dict(bgcolor='#1a2c43',font_color='#d7f3ee'))
 st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
 st.caption('One initial capital point. No profit curve has been invented. With execution unavailable, positions, fees and P&L remain zero. Indicative market prices are never treated as fills.')
with trade_tab:
 st.write('Trade Log: no filled trades — engine disconnected / execution locked.')
 table(pd.DataFrame(store.tickets()))
 st.caption('Only local research drafts appear above. They are not approved tickets or fills.')
with log_tab:
 events=store.events();stages=['All Code Stages']+sorted({english(e['stage']) for e in events})
 choice=st.selectbox('Code-Stage Filter',stages)
 table(pd.DataFrame([{'Time (UTC+6)':local(e['utc']),'Code Stage':e['stage'],'Actual Action / Result':legacy_message(e)} for e in events if choice==stages[0] or english(e['stage'])==choice]))
 st.caption('Historical localized events are summarized in English for display; original evidence is preserved unchanged in SQLite.')
with limits_tab:
 st.write('Owner limits: $50 paper capital · $2.50 maximum trade · 3% maximum slippage · 3 open positions · $2.50 daily realized + unrealized loss entry freeze.')
 st.write('Forbidden: active mint authority, active freeze authority, Token-2022 transfer tax. Missing mandatory evidence blocks fills.')
 st.warning('Effective configuration agreement is UNVERIFIED. Legacy engine defaults reportedly differ. This UI does not modify engagement, risk configuration, approvals, or the desk halt.')
 st.write('Still required: sanctioned engine integration, authoritative gates/configuration, genuine risk/holder/social evidence, fresh same-mint executable route/depth/fees, simulation, exact manual approval, idempotent fills/reconciliation, and mark-to-market position accounting.')
 st.caption('This is a working real-data research scanner, not a completed paper broker. No alternate execution path, live mode, wallet, key handling, signing or broadcast capabilities exist.')
html('<div class="foot">MARKET SCANNER V2 / ENGLISH / DARK · REAL PUBLIC DATA · PAPER RESEARCH ONLY<br>Persistent standalone SQLite evidence · Isolated from old synthetic history · Asia/Dhaka (UTC+6) display / UTC storage</div>')
