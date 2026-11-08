"""Documented DexScreener reads, persistent evidence and fail-closed ticket validation.
No execution implementation exists in this module. It cannot sign or send orders.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import math
import re
import sqlite3
import urllib.request
import urllib.error

API='https://api.dexscreener.com'
DOCS='https://docs.dexscreener.com/api/reference'
CAPITAL=Decimal('50'); MAX_TRADE=Decimal('2.50'); MAX_SLIPPAGE=Decimal('3'); MAX_POSITIONS=3
DAILY_LOSS=Decimal('2.50')
FRESH_SECONDS=60
COOLDOWN_SECONDS=30
CORE_CONNECTED=False  # No adapter; not a setting or a UI toggle.
ROLES={'CHIEF':'Coordination and process oversight','SCOUT':'Market pair discovery','RISK':'Mandatory safety audit',
 'WHALE':'Holder and wallet flow analysis','SHILL':'Social and narrative context','SIGNAL':'Entry signal analysis',
 'SNIPER':'Approved paper entries','RUG':'Position safety monitoring','EXIT':'Approved paper exits','JOURNAL':'Desk ledger and reconciliation'}

def utc():return datetime.now(timezone.utc).isoformat()
def age(stamp):
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()
 except (ValueError,TypeError):return float('inf')
def mint_valid(s):
 if not isinstance(s,str) or not re.fullmatch('[1-9A-HJ-NP-Za-km-z]{32,44}',s):return False
 alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
 n=0
 for ch in s:n=n*58+alphabet.index(ch)
 return (n.bit_length()+7)//8+len(s)-len(s.lstrip('1'))==32

def number(v):
 try:
  if isinstance(v,bool):return None
  x=float(v)
  return x if math.isfinite(x) and x>=0 else None
 except (TypeError,ValueError):return None

class ProviderError(Exception):pass

def get_json(path):
 # Only this fixed public host, no user-supplied URL or credentials.
 req=urllib.request.Request(API+path,headers={'User-Agent':'PumpGrok-ReadOnly-Terminal/1.0','Accept':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=15) as response:
   data=response.read(3_000_001)
   if len(data)>3_000_000:raise ProviderError('Response exceeds 3MB bound')
   if 'json' not in response.headers.get('Content-Type',''):raise ProviderError('Expected JSON content type')
   return json.loads(data),{'url':API+path,'fetched_utc':utc(),'http_date':response.headers.get('Date'),
                            'http_age':response.headers.get('Age'),'provider_observation_utc':None}
 except urllib.error.HTTPError as e:raise ProviderError(f'HTTP {e.code}: {e.reason}') from None
 except urllib.error.URLError as e:raise ProviderError(f'Network error: {e.reason}') from None
 except (ValueError,TimeoutError,OSError) as e:raise ProviderError(f'{type(e).__name__}: {str(e)[:180]}') from None

def parse_profiles(payload):
 if not isinstance(payload,list):raise ProviderError('Invalid discovery schema: list required')
 mints=[]
 for p in payload:
  if isinstance(p,dict) and p.get('chainId')=='solana' and mint_valid(p.get('tokenAddress')):
   if p['tokenAddress'] not in mints:mints.append(p['tokenAddress'])
 return mints[:8]

def parse_pairs(payload,mints,meta):
 if not isinstance(payload,list):raise ProviderError('Invalid pairs schema: list required')
 rows=[];seen=set()
 for p in payload:
  if not isinstance(p,dict) or p.get('chainId')!='solana':continue
  base=p.get('baseToken') or {}; quote=p.get('quoteToken') or {}
  if not isinstance(base,dict) or not isinstance(quote,dict):continue
  mint=base.get('address');pair=p.get('pairAddress')
  if mint not in mints or not mint_valid(mint) or not mint_valid(pair) or pair in seen:continue
  seen.add(pair)
  liquidity=p.get('liquidity') or {};vol=p.get('volume') or {}
  price=number(p.get('priceUsd'))
  if price==0:price=None
  row={'mint':mint,'pair':pair,'symbol':str(base.get('symbol','?'))[:50],
   'quote_symbol':str(quote.get('symbol','?'))[:50],'quote_mint':quote.get('address'),
   'venue':str(p.get('dexId','BLIND'))[:50],'price_usd':price,
   'liquidity_usd':number(liquidity.get('usd')) if isinstance(liquidity,dict) else None,
   'volume_h1_usd':number(vol.get('h1')) if isinstance(vol,dict) else None,
   **meta,'field_sources':{'mint':'baseToken.address','pair':'pairAddress','price_usd':'priceUsd',
   'liquidity_usd':'liquidity.usd','volume_h1_usd':'volume.h1','venue':'dexId'},
   'price_kind':'provider indicative mark, NOT executable quote','risk':'BLIND / NO AUDIT'}
  rows.append(row)
 return rows

def audit(row):
 # DexScreener does not supply on-chain authority/extension/holder/route evidence.
 return {'mint':row['mint'],'pair':row['pair'],'Mint authority':'BLIND — RPC audit not connected',
  'Freeze authority':'BLIND — RPC audit not connected','Token-2022 transfer tax':'BLIND — extension audit missing',
  'Holder / cluster':'BLIND — not performed','Social / narrative':'BLIND — not performed',
  'Route / depth / fees':'BLIND — price mark is not an execution quote',
  'Verdict':'BLOCKED (missing mandatory evidence; NOT a confirmed rug)'}

def halt_status(path=Path('/workspace/pumpgrok/var/desk/KILLSWITCH')):
 # Presence is fail-closed, regardless of contents. Absence is not proof of clearance.
 return 'ACTIVE — halt file present' if Path(path).exists() else 'UNKNOWN — authoritative halt adapter unavailable'

def gate(ticket,row=None,halt=None,config_agrees=False,open_positions=0,daily_pnl=Decimal('0'),audit_clear=False,exact_approval=False):
 reasons=['Desk engine NOT CONNECTED: all fills locked (buy AND sell)']
 reasons.append('Desk halt: '+(halt if halt is not None else halt_status()))
 if not config_agrees:reasons.append('Effective engine configuration not verified against owner limits')
 for field,limit,label in [('usd',MAX_TRADE,'Size must be >0 and ≤ $2.50'),('slippage',MAX_SLIPPAGE,'Slippage must be >0 and ≤ 3%')]:
  try:
   v=Decimal(str(ticket.get(field,'')))
   if not v.is_finite() or not 0<v<=limit:reasons.append(label)
  except Exception:reasons.append(label)
 if open_positions>=MAX_POSITIONS:reasons.append('Max 3 open positions reached')
 if Decimal(str(daily_pnl))<=-DAILY_LOSS:reasons.append('Daily realized + unrealized loss ≥ $2.50: entries frozen')
 if not row or row.get('mint')!=ticket.get('mint') or not 0<=age(row.get('fetched_utc'))<=FRESH_SECONDS:
  reasons.append('Missing / stale / wrong-mint market observation')
 if not audit_clear:reasons.append('Mandatory risk audit BLIND; no RISK CLEAR')
 reasons.append('Executable same-mint route/depth/slippage/fee quote and simulation unavailable')
 if not exact_approval:reasons.append('Exact manual ticket approval not obtained')
 return reasons

class Store:
 def __init__(self,path):
  self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
  with self.db() as c:
   c.executescript('''CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS observations(pair TEXT PRIMARY KEY,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,utc TEXT,stage TEXT,message TEXT);
   CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,kind TEXT,amount_cents INTEGER,utc TEXT);
   ''')
   c.execute("INSERT OR IGNORE INTO ledger VALUES('initial-capital','PAPER_CASH',5000,?)",(utc(),))
 @contextmanager
 def db(self):
  connection=sqlite3.connect(self.path,timeout=10)
  try:
   with connection:yield connection
  finally:connection.close()
 def get(self,key,default=None):
  with self.db() as c:r=c.execute('SELECT v FROM meta WHERE k=?',(key,)).fetchone()
  return json.loads(r[0]) if r else default
 def set(self,key,value):
  with self.db() as c:c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,json.dumps(value)))
 def log(self,stage,message):
  with self.db() as c:c.execute('INSERT INTO events(utc,stage,message) VALUES(?,?,?)',(utc(),stage,message))
 def events(self):
  with self.db() as c:
   c.row_factory=sqlite3.Row
   return [dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 300')]
 def rows(self):
  with self.db() as c:return [json.loads(r[0]) for r in c.execute('SELECT payload FROM observations ORDER BY pair')]
 def save_rows(self,rows):
  added=0
  with self.db() as c:
   for r in rows:
    fingerprint={k:v for k,v in r.items() if k not in ['fetched_utc','http_date','http_age']}
    key=hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    added+=c.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?)',(key,json.dumps(r))).rowcount
    c.execute('INSERT OR REPLACE INTO observations VALUES(?,?)',(r['pair'],json.dumps(r)))
  return added
 def cash(self):
  with self.db() as c:return c.execute('SELECT SUM(amount_cents) FROM ledger').fetchone()[0]/100
 def ticket(self,ticket):
  key=hashlib.sha256(json.dumps(ticket,sort_keys=True).encode()).hexdigest()
  payload={**ticket,'status':'RESEARCH DRAFT — NOT APPROVED / FILLS LOCKED','created_utc':utc()}
  with self.db() as c:c.execute('INSERT OR IGNORE INTO tickets VALUES(?,?)',(key,json.dumps(payload)))
  return key
 def tickets(self):
  with self.db() as c:return [json.loads(x[0]) for x in c.execute('SELECT payload FROM tickets')]

def scan(store,fetch=get_json,progress=None):
 if store.get('provider_blocked',False):
  return {'cached':True,'new':0,'message':'Provider denied access; stopped. No alternate route attempted.'}
 if age(store.get('last_attempt'))<COOLDOWN_SECONDS:
  return {'cached':True,'new':0,'message':'30s provider cooldown; last-good cache reused; scan counters unchanged'}
 # Transactional scan lease prevents overlapping sessions from spamming the provider.
 with store.db() as c:
  c.execute('BEGIN IMMEDIATE')
  r=c.execute("SELECT v FROM meta WHERE k='last_attempt'").fetchone()
  if r and age(json.loads(r[0]))<COOLDOWN_SECONDS:
   return {'cached':True,'new':0,'message':'Another session holds cooldown; cached data only'}
  c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('last_attempt',json.dumps(utc())))
 def step(stage,text):
  store.log(stage,text)
  if progress:progress(stage,text)
 try:
  step('CODE / DISCOVERY','Fetching real DexScreener latest profiles; profiles do not guarantee newly launched tokens.')
  payload,meta=fetch('/token-profiles/latest/v1');mints=parse_profiles(payload)
  if not mints:raise ProviderError('No valid Solana mint identities in latest profiles')
  step('CODE / MARKET',f'Fetching public pair data for {len(mints)} exact Solana mints.')
  raw,meta=fetch('/tokens/v1/solana/'+','.join(mints))
  rows=parse_pairs(raw,mints,meta)
  if not rows:raise ProviderError('No valid same-mint Solana pair records; no fallback data generated')
  new=store.save_rows(rows)
  step('CODE / EVIDENCE',f'Validated {len(rows)} real pairs; {new} new data snapshots. Authority/Token-2022/route audit BLIND; fills locked.')
  health={'status':'OK','utc':utc(),'pairs':len(rows),'mints':mints,'source':meta,'error':None}
  store.set('health',health);store.set('last_success',utc())
  step('CODE / JOURNAL','Real observations and provenance saved to SQLite. No trades were placed.')
  return {'cached':False,'new':new,'message':f'{len(rows)} real pairs observed; no orders; missing evidence blocks all fills'}
 except Exception as e:
  # No credentials/response bodies included. A denied provider is latched off, never rerouted.
  error=(f'{type(e).__name__}: {str(e)}')[:240]
  denied=any(t in error.lower() for t in ['http 403','http 451','proxy','blocked','forbidden'])
  store.set('health',{'status':'BLOCKED' if denied else 'ERROR','utc':utc(),'error':error})
  if denied:store.set('provider_blocked',True)
  step('CODE / ERROR',error+' — last-good data retained; no synthetic fallback')
  return {'cached':False,'new':0,'message':error}
