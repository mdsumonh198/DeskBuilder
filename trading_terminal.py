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

import time
import copy
from html import escape

STAGES = [
 ('CHIEF','পরিকল্পনা','এই অনুশীলনের ছয়টি কৃত্রিম pair যাচাইয়ের পরিকল্পনা করছে।','ইনপুট: ডেমো capital ও ছয়টি বানানো pair','পরিকল্পনা প্রস্তুত; কোনো আসল agent-কে কাজ দেওয়া হয়নি।'),
 ('SCOUT','নমুনা pair খোঁজা','ছয়টি বানানো token pair স্ক্যান করছে; কোনো বাজার থেকে তথ্য নিচ্ছে না।','ইনপুট: deterministic demo generator','ছয়টি কৃত্রিম pair পাওয়া গেছে।'),
 ('RISK','নমুনা ঝুঁকি যাচাই','বানানো liquidity ও concentration flag পরীক্ষা করছে।','ইনপুট: ছয়টি কৃত্রিম pair','দুটি ডেমো pair বাদ; চারটি পরের ধাপে। এটি আসল safety clearance নয়।'),
 ('WHALE','নমুনা holder বিশ্লেষণ','চারটি pair-এর কাল্পনিক holder distribution দেখছে।','ইনপুট: চারটি রাখা pair; কোনো wallet data নয়','কাল্পনিক holder check শেষ; আসল holder যাচাই হয়নি।'),
 ('SHILL','নমুনা social বিশ্লেষণ','বানানো narrative context পড়ছে; X বা social feed ব্যবহার করছে না।','ইনপুট: কৃত্রিম narrative text','Mock social context নথিভুক্ত; বাস্তব sentiment অজানা।'),
 ('SIGNAL','নমুনা score ও size','ডেমো score হিসাব করে দুটি কাল্পনিক trade নির্বাচন করছে।','ইনপুট: demo score ও illustrative sizing rule','দুটি ডেমো entry নির্বাচিত; দুটি watch-only। এটি buy recommendation নয়।'),
 ('SNIPER','কাগুজে entry','শুধু এই UI-এর স্মৃতিতে দুটি কাল্পনিক entry তৈরি করছে।','ইনপুট: দুটি নির্বাচিত ডেমো pair','দুটি virtual entry প্রস্তুত; কোনো বাস্তব order পাঠানো হয়নি।'),
 ('RUG','কাল্পনিক position watch','ডেমো entry দুটির জন্য বানানো threat scenario দেখছে।','ইনপুট: দুটি virtual position','Mock watch শেষ; বাস্তব position বা threat monitoring নেই।'),
 ('EXIT','কাগুজে close','কাল্পনিক exit ও illustrative fee হিসাব করছে।','ইনপুট: demo entry, synthetic return, 0.20% illustrative fee','দুটি virtual close গণনা শেষ; JOURNAL-এ একবারই balance লেখা হবে।'),
 ('JOURNAL','হিসাব ও সারাংশ','ডেমো ledger, balance, equity ও log একবার আপডেট করছে।','ইনপুট: দুটি virtual round trip','ডেমো cycle শেষ। সব কাগুজে position closed; ledger মিলেছে।')]
ORDER=[x[0] for x in STAGES]

def fresh():
 return {'cycle':0,'balance':INITIAL,'scanned':0,'blocked':0,'trades':[],'scanner':[],'activity':[],
         'last':'—','equity':[{'Cycle':0,'Equity ($)':INITIAL,'Time':now().isoformat()}]}

# Migrate old instantaneous/preloaded demo state: keep its ledger visibly separate.
if st.session_state.get('activity_ui_version') != 3:
 old=st.session_state.get('terminal')
 if old:
  st.session_state['previous_demo_summary']={'cycles':old.get('cycle',0),'balance':old.get('balance',INITIAL)}
 st.session_state['terminal']=fresh()
 st.session_state['playback']={'running':False,'index':0,'cycle_id':0,'settled':False,'completed':False,'timeline':[]}
 st.session_state['activity_ui_version']=3
s=st.session_state['terminal']; play=st.session_state['playback']

def start_cycle():
 if play['running']:return
 preview=copy.deepcopy(s)
 cycle(preview)  # Pure session-local forecast; never mutates the displayed ledger.
 play.update(running=True,index=0,cycle_id=s['cycle']+1,settled=False,completed=False,
             due=time.monotonic()+2.0,preview=preview)

def advance_stage():
 if not play['running']:return
 idx=play['index']; name,title,action,inputs,result=STAGES[idx]
 stamp=now().strftime('%H:%M:%S')
 play['timeline'].append({'Cycle':f'DEMO-{play["cycle_id"]:03d}','Time (UTC+6)':stamp,
  'Agent':name,'কাজ':title,'ডেমো ইনপুট':inputs,'কৃত্রিম ফল / সিদ্ধান্ত':result,'অবস্থা':'শেষ · DEMO'})
 if idx==9:
  if not play['settled']:
   forecast=play['preview']
   # One atomic settlement per user-triggered cycle; no rerun can re-book it.
   for key in ['cycle','balance','scanned','blocked','trades','scanner','equity']:
    s[key]=forecast[key]
   s['last']=stamp
   s['activity']=[{'Time (UTC+6)':r['Time (UTC+6)'],'Agent':r['Agent'],
       'Simulated activity':r['কাজ']+' — '+r['কৃত্রিম ফল / সিদ্ধান্ত']} for r in play['timeline']]
   play['settled']=True
  play.update(running=False,completed=True,index=10)
 else:
  play['index']+=1;play['due']=time.monotonic()+2.0

# No loop, sleeps, worker, or scheduled activity. Timer exists only for one requested demo cycle.
@st.fragment(run_every=1 if play['running'] else None)
def tick():
 if play['running'] and time.monotonic()>=play['due']:
  advance_stage()
  st.rerun()
tick()

st.markdown('''<style>
:root{color-scheme:light!important}.stApp,[data-testid="stAppViewContainer"]{background:#fafafa!important;color:#303941!important}
body,p,span,label,button,input{font-family:"Noto Sans Bengali","Nirmala UI","Vrinda",system-ui,sans-serif!important}
[data-testid="stHeader"]{background:transparent}.block-container{max-width:1280px;padding:2rem 1.5rem}
[data-testid="stVerticalBlock"]{gap:.7rem}p{font-size:14px;color:#4b555f}.mono,.brand,.money,.tiny{font-family:ui-monospace,Consolas,monospace!important}
.header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px dashed #d4d9df;padding-bottom:16px;margin-bottom:4px}.brand{font-size:23px;font-weight:700;color:#30353e}.brand b{color:#437bdf}.pause{display:inline-grid;place-items:center;background:#eceef1;color:#a1a9b1;border-radius:50%;width:42px;height:42px;margin-right:12px;font-size:18px}.money{font-size:27px;text-align:right}.tiny{font-size:11px;color:#73808c}.green{color:#2d9161}.pink{color:#bf6385}.badge{font-size:11px;color:#54795f;background:#e8f3eb;border:1px solid #c5dfcd;border-radius:5px;padding:4px 7px}
.current{border:1px solid #afd6c0;border-left:5px solid #5aa97e;border-radius:10px;background:#f1f8f4;padding:20px;margin-bottom:4px}.current.idle{background:#f3f5f8;border-color:#cbd3df;border-left-color:#8c9db5}.eyebrow{font-size:12px;color:#647a6e;font-weight:600}.current h2{font-size:25px;margin:8px 0 10px;line-height:1.4;color:#283c31}.current p{font-size:16px;line-height:1.7;margin:6px 0}.next{margin-top:12px;padding-top:12px;border-top:1px dashed #bfcfc4;color:#54725f;font-size:14px}.finding{background:#fff;border:1px solid #dfebe3;border-radius:6px;padding:10px;font-size:14px;color:#52675a;margin-top:10px}
.seat{border:1px solid #e0e4e9;background:#fff;border-radius:8px;padding:12px;margin-bottom:8px}.seat.active{background:#edf8f1;border:2px solid #71b68c}.seat.done{border-color:#cce0d2}.seat-head{display:flex;justify-content:space-between;align-items:center;font:600 13px monospace;color:#53566c}.seat p{font-size:12px;margin:5px 0 0;color:#67727e}.status{font-size:11px;color:#8b7d9b;background:#f1edf7;padding:3px 5px;border-radius:4px}.active .status{background:#cfe9d8;color:#256d47}.done .status{background:#ebf3ed;color:#598568}
[data-testid="stMetric"]{border:1px solid #e2e5e9;background:#fff;border-radius:8px;padding:12px}[data-testid="stMetricValue"]{font-family:monospace;font-size:24px;color:#394b45}[data-testid="stMetricLabel"] p{font-size:12px}
.stButton>button{background:#edf6f0!important;color:#32684a!important;border:1px solid #b4d4c0!important;border-radius:6px;min-height:40px}.stButton>button p{font-size:14px!important;color:#32684a!important}.stButton>button:disabled{opacity:.5}[data-baseweb="tab"]{font-size:13px!important;color:#647383!important}[data-baseweb="tab-highlight"]{background:#7ba4cb!important}[data-testid="stCaptionContainer"] p{font-size:12px;color:#74818d}
.log{border-bottom:1px solid #e5e8ec;padding:11px 0;display:grid;grid-template-columns:100px 80px 1fr;gap:12px;font-size:13px;color:#57636d}.log b{color:#69628a;font-family:monospace}.log small{color:#86909a}.log div:last-child{line-height:1.7}.log .decision{color:#557b63}.section{font-size:13px;font-weight:700;letter-spacing:.5px;color:#6c7b87;border-bottom:1px dashed #d9dfe4;padding:12px 0 8px}
@media(max-width:760px){.block-container{padding:1.6rem .8rem}.brand{font-size:18px}.pause{display:none}.money{font-size:21px}.current{padding:15px}.current h2{font-size:22px}.current p{font-size:15px}.log{grid-template-columns:75px 65px 1fr;font-size:12px;gap:5px}.header{gap:8px}}
</style>''',unsafe_allow_html=True)

def html(x):st.markdown(x,unsafe_allow_html=True)
pnl=round(s['balance']-INITIAL,2)
html(f'<div class="header"><div><div class="brand"><span class="pause">Ⅱ</span><b>Grok Bot</b> Terminal</div><div class="tiny">PUMPGROK / SYNTHETIC DEMO · UTC+6</div></div><div><div class="money">${s["balance"]:,.2f}</div><div class="tiny">ডেমো balance · {len(s["trades"])} paper trades</div></div></div>')
st.warning('শুধু অনুশীলন—আসল agent বা বাজারের সঙ্গে সংযোগ নেই। নিচের সব কাজ ও ফল এই UI-এর কৃত্রিম simulation; আসল PumpGrok desk অপরিবর্তিত।')
if 'previous_demo_summary' in st.session_state:
 st.caption('নতুন ধাপে-ধাপে UI শুরু হয়েছে। আগের সংস্করণের sample/demo history নতুন user-run cycle থেকে আলাদা করা হয়েছে; এই session-এর হিসাব $10,000 illustrative capital থেকে নতুন করে শুরু।')

if play['running']:
 idx=play['index']; name,title,action,inputs,result=STAGES[idx]
 next_text=(f'{STAGES[idx+1][0]} — {STAGES[idx+1][1]}' if idx<9 else 'cycle শেষ; কোনো কাজ চলবে না')
 current_done=[r for r in play['timeline'] if r['Cycle']==f'DEMO-{play["cycle_id"]:03d}']
 previous=current_done[-1]['কৃত্রিম ফল / সিদ্ধান্ত'] if current_done else 'এই cycle-এ এখনও কোনো ধাপ শেষ হয়নি।'
 html(f'<div class="current"><div class="eyebrow">এখন কী হচ্ছে · DEMO-{play["cycle_id"]:03d} · ধাপ {idx+1}/10</div><h2>● {name} — {title}</h2><p>{action}</p><p>{inputs}</p><div class="finding">আগের ধাপের ফল: {escape(previous)}</div><div class="next">এরপর: {next_text}<br>প্রতি প্রায় ২ সেকেন্ডে পরের ধাপ; নিচের বাটন দিয়েও এগোনো যায়।</div></div>')
else:
 message='শেষ ডেমো cycle সম্পূর্ণ হয়েছে।' if play['completed'] else 'এখন কোনো কাজ চলছে না—cycle শুরু করুন।'
 html(f'<div class="current idle"><div class="eyebrow">এখন কী হচ্ছে · IDLE / DEMO</div><h2>{message}</h2><p>দশটি simulated agent-এর কাজ একে একে দেখতে <b>Run Scanner Cycle</b> চাপুন। কোনো আসল agent কাজ শুরু করবে না।</p><div class="next">পরের কাজ: CHIEF পরিকল্পনা → SCOUT নমুনা scan।<br>কোনো background scan বা বাস্তব monitoring চলছে না।</div></div>')
st.progress(play['index']/10 if (play['running'] or play['completed']) else 0,
 text=f'ডেমো অগ্রগতি: {play["index"]}/10 ধাপ শেষ')
a,b,c=st.columns([1.3,1,2])
with a:st.button('Run Scanner Cycle',on_click=start_cycle,disabled=play['running'],width='stretch')
with b:st.button('পরের ধাপ',on_click=advance_stage,disabled=not play['running'],width='stretch')
with c:st.caption('একবারে একটি cycle। শেষ ধাপে ledger একবার লেখা হয়। খোলা browser-এ শুধু এই cycle-এর demo playback চলবে।')
metrics=st.columns(4)
metrics[0].metric('অনুশীলনের balance',f'${s["balance"]:,.2f}')
metrics[1].metric('ডেমো net P&L',f'${pnl:+,.2f}')
metrics[2].metric('স্ক্যান করা নমুনা pair',s['scanned'])
metrics[3].metric('বাদ দেওয়া ডেমো ঝুঁকি',s['blocked'])
if play['running']:st.caption('চলমান cycle-এর ফল এখনও provisional। JOURNAL ধাপ শেষ হলে উপরের হিসাব, equity ও trade log একসঙ্গে আপডেট হবে।')
rail,body=st.columns([1,2.7],gap='large')
with rail:
 html('<div class="section">কোন agent কী করে · সবই DEMO</div>')
 for idx,(name,title,action,inputs,result) in enumerate(STAGES):
  active=play['running'] and play['index']==idx
  done=(play['running'] and idx<play['index']) or play['completed']
  status='চলছে · DEMO' if active else ('শেষ · DEMO' if done else 'অপেক্ষা · DEMO')
  html(f'<div class="seat {"active" if active else "done" if done else ""}"><div class="seat-head">{idx+1:02d} {name}<span class="status">{status}</span></div><p>{title}</p></div>')
with body:
 html('<div class="section">এই cycle-এ যা হয়েছে · chronological activity</div>')
 current_logs=[r for r in play['timeline'] if r['Cycle']==f'DEMO-{play["cycle_id"]:03d}']
 if not current_logs:st.info('এখনও কোনো ধাপ শেষ হয়নি। cycle শুরু হলে প্রতিটি agent-এর ইনপুট, কাজ ও ডেমো ফল এখানে আসবে।')
 for r in current_logs:
  html(f'<div class="log"><div><small>{r["Time (UTC+6)"]}<br>UTC+6</small></div><b>{r["Agent"]}</b><div><strong>{r["কাজ"]} — শেষ</strong><br>{r["ডেমো ইনপুট"]}<br><span class="decision">ফল: {r["কৃত্রিম ফল / সিদ্ধান্ত"]}</span></div></div>')
 html('<div class="section">Equity curve · শুধু settled demo balance</div>')
 eq=pd.DataFrame(s['equity']);low=eq['Equity ($)'].min();high=eq['Equity ($)'].max();pad=max((high-low)*.3,15)
 fig=go.Figure(go.Scatter(x=eq['Cycle'],y=eq['Equity ($)'],mode='lines+markers',line=dict(color='#73ae8b',width=2),
  hovertemplate='Demo cycle %{x}<br>Paper equity $%{y:,.2f}<extra></extra>'))
 fig.update_layout(height=210,margin=dict(l=5,r=10,t=10,b=30),paper_bgcolor='#fafafa',plot_bgcolor='#fafafa',
  font=dict(family='monospace',size=11,color='#76818c'),xaxis=dict(title='Completed demo cycle',dtick=1,gridcolor='#eceef0'),
  yaxis=dict(title='Paper USD',tickprefix='$',range=[low-pad,high+pad],gridcolor='#eceef0'))
 st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})

scanner_tab,trades_tab,logs_tab=st.tabs(['নমুনা scanner feed','Paper trade log','সব agent-এর activity'])
def table(frame):
 if frame.empty:
  st.caption('এখনও কোনো settled demo record নেই।');return
 st.dataframe(frame.style.set_properties(**{'background-color':'white','color':'#4e5b67','font-size':'13px'}),hide_index=True,width='stretch',height=300)
with scanner_tab:
 st.caption('আসল live feed নয়। SCOUT ধাপ শেষ হলে provisional নমুনা দেখা যায়; JOURNAL শেষে settled হয়।')
 if play['running'] and play['index']>=2:
  st.caption('চলমান cycle · provisional synthetic candidates')
  candidates=pd.DataFrame(play['preview']['scanner'][-6:]).copy()
  if play['index']<3:
   candidates=candidates.drop(columns=['Decision','Reason','Score'])
  elif play['index']<7:
   candidates['Decision']=candidates['Decision'].replace({'PAPER FILLED':'DEMO CANDIDATE'})
   candidates['Reason']=candidates['Reason'].replace({'Round trip closed':'ডেমো entry এখনও হয়নি'})
  table(candidates)
 else:table(pd.DataFrame(s['scanner'][::-1]))
with trades_tab:
 st.caption('কাগুজে round trip; কোনো আসল order নয়। Entry → watch → close → JOURNAL শেষে net fees-সহ ledger লেখা হয়।')
 table(pd.DataFrame(s['trades'][::-1]))
with logs_tab:
 agent=st.selectbox('Filter simulated agent',['All agents']+ORDER)
 table(pd.DataFrame([r for r in play['timeline'] if agent=='All agents' or r['Agent']==agent]))
st.caption('SIMULATED PAPER ONLY · Illustrative starting capital $10,000 · Round-trip illustrative fee 0.20% · Session-local history; restart/new session resets it · Asia/Dhaka (UTC+6).')
