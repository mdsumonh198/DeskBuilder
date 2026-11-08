"""PumpGrok Paper System v3: standalone, read-only market + local simulated broker.
No wallet support, transaction construction, chain simulation, signing or broadcasting.
No assistant Bots are connected. Default unknown/halted desk gates block all fills.
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
 # public_json is resolved when called, after this self-contained module loads.
 return public_json(API+path)

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

class ResearchStore:
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
  step('CODE / EVIDENCE',f'Validated {len(rows)} real pairs; {new} new data snapshots. Market data saved. Run explicit authority audit and route quote; desk gates still required.')
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



# ---- Paper engine: decimal event sourcing; no network order capability ----
import os
import base64
import uuid
import csv
import io
from email.utils import parsedate_to_datetime
from datetime import timedelta
from decimal import InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, getcontext
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

getcontext().prec=50
TZ=ZoneInfo('Asia/Dhaka')
SPL='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
TOKEN2022='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
RPC='https://api.mainnet-beta.solana.com'
JUP='https://api.jup.ag/swap/v2/order'
KILL_PATH=Path('/workspace/pumpgrok/var/desk/KILLSWITCH')
POLICY={'mode':'paper','capital_usd':'50','max_trade_usd':'2.50','max_slippage_pct':'3',
        'max_positions':3,'daily_loss_usd':'2.50','timezone':'Asia/Dhaka','approval':'manual-exact',
        'forbid_mint_authority':True,'forbid_freeze_authority':True,'forbid_transfer_tax':True}
MODEL='route-adverse-25bp-fee-30bp-plus-1cent-v1'
RULES='research-liq10k-vol1k-v1'

class Blocked(Exception):pass
class UnknownResult(Exception):pass

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def dec(x):
 if isinstance(x,bool):raise Blocked('Boolean is not a number')
 try:
  text=str(x)
  if len(text)>100:raise Blocked('Numeric evidence exceeds bound')
  d=Decimal(text)
  if not d.is_finite():raise Blocked('Non-finite number')
  if d and not -30<=d.adjusted()<=30:raise Blocked('Numeric exponent outside supported bounds')
  return d
 except (InvalidOperation,ValueError,TypeError):raise Blocked('Missing or malformed numeric evidence') from None

def money(x):return dec(x).quantize(Decimal('.00000001'),rounding=ROUND_HALF_UP)
def qty(x):return dec(x).quantize(Decimal('.000000000000000001'),rounding=ROUND_DOWN)
def stamp(t=None):return (t or datetime.now(timezone.utc)).isoformat()
def seconds(s,now):
 try:
  d=datetime.fromisoformat(s.replace('Z','+00:00'))
  if d.tzinfo is None:return float('inf')
  return (now-d).total_seconds()
 except (ValueError,TypeError,AttributeError):return float('inf')
def recent(s,now,limit=60):return 0<=seconds(s,now)<=limit

def provenance_ok(meta,now,limit=60):
 """Retrieval age plus HTTP intermediary age. Unknown market event time stays unknown."""
 if not recent(meta.get('fetched_utc'),now,limit):return False
 try:
  cache_age=int(meta.get('http_age') or 0)
  date=parsedate_to_datetime(meta['http_date'])
  elapsed=(now-date).total_seconds()
  return cache_age>=0 and seconds(meta['fetched_utc'],now)+cache_age<=limit and -5<=elapsed<=limit
 except (ValueError,TypeError,KeyError,OverflowError):return False

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ProviderError('Redirect refused; provider stopped')

def public_json(url,body=None):
 """Fixed allowlist, bounded response, no credentials, retries, redirects or fallback hosts."""
 allowed=(url.startswith(API+'/') or url.startswith(JUP+'?') or url==RPC)
 if not allowed:raise ProviderError('Unapproved public endpoint')
 data=None if body is None else canonical(body).encode()
 req=urllib.request.Request(url,data=data,headers={'Accept':'application/json','Content-Type':'application/json',
  'User-Agent':'PumpGrok-Paper-ReadOnly/3','Cache-Control':'no-cache'})
 try:
  with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as r:
   content=r.read(3_000_001)
   if len(content)>3_000_000 or 'json' not in r.headers.get('Content-Type',''):
    raise ProviderError('Invalid content type or response size')
   return json.loads(content),{'url':url,'fetched_utc':utc(),'http_date':r.headers.get('Date'),
    'http_age':r.headers.get('Age'),'provider_observation_utc':None}
 except urllib.error.HTTPError as e:
  raise ProviderError(f'HTTP {e.code}; source stopped; no alternate endpoint') from None
 except (urllib.error.URLError,TimeoutError,OSError,ValueError):
  raise ProviderError('Public provider unavailable or malformed JSON; no synthetic fallback') from None

# Replace old network helper without changing discovery/parser/storage behavior.
def get_json(path):return public_json(API+path)

def read_market(mint,fetch=public_json):
 if not mint_valid(mint):raise Blocked('Invalid mint identity')
 payload,meta=fetch(API+'/tokens/v1/solana/'+mint)
 rows=parse_pairs(payload,[mint],meta)
 if not rows:raise ProviderError('No valid same-mint market observations')
 return rows

def parse_authority(payload,mint,meta):
 result={'mint':mint,**meta,'subset_verdict':'BLIND','reasons':[],
         'scope':'CODE authority/extension subset only; NOT RISK Bot CLEAR'}
 try:
  if not mint_valid(mint) or not isinstance(payload,dict) or payload.get('error'):raise Blocked('RPC identity/error')
  data=payload['result'];value=data['value'];slot=data['context']['slot']
  if type(slot) is not int or slot<=0 or not isinstance(value,dict):raise Blocked('Missing finalized account/slot')
  if value.get('executable') is not False:raise Blocked('Executable or unknown account')
  owner=value['owner']
  if owner not in (SPL,TOKEN2022):raise Blocked('Unrecognized mint program')
  parsed=value['data']
  if parsed['program'] not in ('spl-token','spl-token-2022') or parsed['parsed']['type']!='mint':raise Blocked('Not a parsed mint')
  if parsed['program']!=('spl-token' if owner==SPL else 'spl-token-2022'):raise Blocked('Parser/owner mismatch')
  info=parsed['parsed']['info']
  for field in ('mintAuthority','freezeAuthority','decimals','isInitialized','supply'):
   if field not in info:raise Blocked('Missing '+field)
  decimals=info['decimals']
  if type(decimals) is not int or not 0<=decimals<=18 or info['isInitialized'] is not True:
   raise Blocked('Invalid mint decimals/initialization')
  if not isinstance(info['supply'],str) or not info['supply'].isdigit():raise Blocked('Invalid supply')
  result.update(program=owner,slot=slot,decimals=decimals,mint_authority=info['mintAuthority'],
   freeze_authority=info['freezeAuthority'],transfer_tax=False,raw_hash=digest(payload))
  for field in ('mintAuthority','freezeAuthority'):
   if info[field] is not None:result['reasons'].append('FORBIDDEN active '+field)
  if owner==TOKEN2022:
   extensions=info.get('extensions')
   if extensions is None and parsed.get('space')==82:extensions=[]
   if not isinstance(extensions,list):raise Blocked('Token-2022 extension inventory unavailable')
   result['extensions']=extensions
   for ext in extensions:
    if not isinstance(ext,dict):raise Blocked('Malformed extension')
    name=ext.get('extension')
    if name=='transferFeeConfig':
     state=ext.get('state',{})
     for schedule in ('olderTransferFee','newerTransferFee'):
      fee=state.get(schedule,{})
      if 'transferFeeBasisPoints' not in fee:raise Blocked('Transfer fee schedule unavailable')
      bps=dec(fee['transferFeeBasisPoints'])
      if bps!=bps.to_integral_value() or not 0<=bps<=10000:raise Blocked('Invalid transfer fee basis points')
      if bps>0:
       result['transfer_tax']=True;result['reasons'].append('FORBIDDEN Token-2022 transfer tax')
     if state.get('transferFeeConfigAuthority','UNKNOWN') is not None:
      raise Blocked('Mutable/unknown transfer fee authority')
    elif name not in ('metadataPointer','tokenMetadata'):
     raise Blocked('Unsupported security-relevant extension: '+str(name))
  result['subset_verdict']='FORBIDDEN' if result['reasons'] else 'PASS SUBSET'
 except (KeyError,TypeError,ValueError,Blocked) as e:result['reasons'].append(str(e))
 result['audit_id']=digest(result)
 return result

def read_authority(mint,fetch=public_json):
 if not mint_valid(mint):raise Blocked('Invalid mint')
 body={'jsonrpc':'2.0','id':1,'method':'getAccountInfo',
  'params':[mint,{'encoding':'jsonParsed','commitment':'finalized'}]}
 raw,meta=fetch(RPC,body)
 return parse_authority(raw,mint,meta)

def candidate(row):
 """Research filter only; no automatic order or strategy promotion."""
 findings=[]
 for k,minimum in [('liquidity_usd','10000'),('volume_h1_usd','1000')]:
  try:findings.append(k+(': PASS' if dec(row.get(k))>=dec(minimum) else ': BELOW '+minimum))
  except Blocked:findings.append(k+': BLIND')
 return {'rule_version':RULES,'status':'RESEARCH ONLY — replay + human promotion required',
  'findings':findings,'proposed_exit_rules':'Research only: -10% stop / +20% take-profit; never auto-sells',
  'profitability':'UNKNOWN; no profitability claim or measured win rate'}

class DeskEvidence:
 """Read-only, signed short-lived gate contract. No signer or clearance writer exists here.
 A sanctioned owner-provisioned bridge must publish the evidence; currently absent.
 Public verification key is not a wallet key. No UI/config toggle can assert clearance.
 """
 def __init__(self,path=None,public_key=None,kill_path=KILL_PATH):
  self.path=path or os.environ.get('PUMPGROK_GATE_ATTESTATION')
  self.public_key=public_key or os.environ.get('PUMPGROK_GATE_PUBLIC_KEY')
  self.kill_path=Path(kill_path)
 def read(self,now):
  if self.kill_path.exists():raise Blocked('GLOBAL KILL ACTIVE — all paper buys/sells blocked')
  if not self.path or not self.public_key:
   raise Blocked('Desk disconnected / halt UNKNOWN / configuration UNVERIFIED; signed bridge missing')
  try:
   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
   path=Path(self.path)
   if path.stat().st_size>300000:raise Blocked('Oversized desk evidence')
   envelope=json.loads(path.read_text())
   payload=envelope['payload']
   Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key)).verify(
    base64.b64decode(envelope['signature'],validate=True),canonical(payload).encode())
   if payload.get('audience')!='pumpgrok-standalone-paper-v3':raise Blocked('Wrong gate audience')
   if not recent(payload.get('issued_utc'),now,30):raise Blocked('Stale/future authoritative desk status')
   expiry=datetime.fromisoformat(payload['expires_utc'])
   if not 0<(expiry-now).total_seconds()<=60:raise Blocked('Gate expiry invalid')
   if payload.get('halt')!='CLEAR' or payload.get('authoritative') is not True:
    raise Blocked('Authoritative halt not CLEAR')
   if payload.get('policy')!=POLICY:raise Blocked('Effective policy differs from owner USD limits')
   if payload.get('strategy')!={'version':RULES,'replay_passed':True,'human_promoted':True,'model':MODEL}:
    raise Blocked('Research rules / modeled execution not replayed and human-promoted')
   if not re.fullmatch('[0-9a-f]{64}',str(payload.get('owner_identity_hash',''))):raise Blocked('Verified owner identity binding missing')
   if not payload.get('evidence_id') or not payload.get('owner_authorization_id'):
    raise Blocked('Missing owner integration authorization / evidence receipt')
   return {**payload,'verification':{'signature':envelope['signature'],'public_key':self.public_key,'signed_payload_hash':digest(payload)}}
  except Blocked:raise
  except Exception:raise Blocked('Invalid/untrusted/missing signed desk evidence') from None

class RouteModel:
 """Quote -> deterministic PAPER simulation. No executable transaction or chain simulation.
 Real Jupiter route output is informational; modeled adverse buffer + fees are estimates.
 """
 @staticmethod
 def request(ticket,audit,fetch=public_json):
  side=ticket['side'];mint=ticket['mint'];d=audit['decimals']
  if side=='BUY':a=int(dec(ticket['usd'])*1_000_000);input_mint=USDC;output_mint=mint
  else:a=int(dec(ticket['quantity'])*(10**d));input_mint=mint;output_mint=USDC
  if a<=0:raise Blocked('Order rounds to zero atomic units')
  params={'inputMint':input_mint,'outputMint':output_mint,'amount':str(a),
   'slippageBps':int(dec(ticket['slippage_pct'])*100)}
  raw,meta=fetch(JUP+'?'+urlencode(params))
  return RouteModel.parse(raw,meta,ticket,audit,a,input_mint,output_mint)
 @staticmethod
 def parse(raw,meta,ticket,audit,amount,input_mint,output_mint):
  try:
   if not isinstance(raw,dict) or raw.get('error') or raw.get('errorCode') or raw.get('transaction') or raw.get('taker'):
    raise Blocked('Invalid quote or unexpected transaction/wallet fields')
   if raw.get('inputMint')!=input_mint or raw.get('outputMint')!=output_mint:
    raise Blocked('Route mint mismatch')
   if str(raw.get('inAmount'))!=str(amount) or raw.get('swapMode')!='ExactIn':raise Blocked('Route input amount mismatch')
   if dec(raw.get('slippageBps'))!=dec(ticket['slippage_pct'])*100:raise Blocked('Quote slippage mismatch')
   route=raw.get('routePlan')
   if not isinstance(route,list) or not route or len(route)>100:raise Blocked('Route/depth evidence missing or excessive')
   for step in route:
    swap=step['swapInfo']
    if not mint_valid(swap['ammKey']) or not mint_valid(swap['inputMint']) or not mint_valid(swap['outputMint']):
     raise Blocked('Malformed route identities')
    for field in ('inAmount','outAmount'):
     amount_value=dec(swap[field])
     if amount_value<=0 or amount_value!=amount_value.to_integral_value():raise Blocked('Invalid route depth atomic amounts')
    if not 0<dec(step['bps'])<=10000 or not 0<dec(step['percent'])<=100:raise Blocked('Invalid route allocation')
   reachable={input_mint}
   for _ in route:
    for step in route:
     swap=step['swapInfo']
     if swap['inputMint'] in reachable:reachable.add(swap['outputMint'])
   if output_mint not in reachable or any(s['swapInfo']['inputMint'] not in reachable for s in route):raise Blocked('Disconnected route plan')
   out=dec(raw['outAmount']);impact=abs(dec(raw['priceImpact']))
   if out<=0 or out!=out.to_integral_value():raise Blocked('Invalid output atomic units')
   if impact>dec(ticket['slippage_pct']):raise Blocked('Route impact exceeds slippage cap')
   # Zero fee fields may be promotional; model always reserves conservative fee.
   fees={k:str(dec(raw[k])) for k in ('feeBps','signatureFeeLamports','prioritizationFeeLamports','rentFeeLamports')}
   if any(dec(x)<0 for x in fees.values()):raise Blocked('Negative quote fee')
   if any(dec(fees[k])>0 for k in ('signatureFeeLamports','prioritizationFeeLamports','rentFeeLamports')):
    raise Blocked('Nonzero network fees require a fresh verified SOL/USD conversion; not connected')
   if not raw.get('requestId') or not meta.get('url','').startswith(JUP+'?'):raise Blocked('Missing quote provenance')
   q={'mint':ticket['mint'],'pair':ticket['pair'],'side':ticket['side'],'amount_atomic':str(amount),
    'output_atomic':str(out),'input_mint':input_mint,'output_mint':output_mint,'route':route,
    'impact_pct':str(impact),'fee_evidence':fees,'request_id':raw['requestId'],
    'in_usd':str(dec(raw['inUsdValue'])),'out_usd':str(dec(raw['outUsdValue'])),
    'decimals':audit['decimals'],'slippage_pct':str(dec(ticket['slippage_pct'])),'model':MODEL,'kind':'MODELED PAPER / genuine informational route',**meta}
   if dec(q['in_usd'])<=0 or dec(q['out_usd'])<=0:raise Blocked('Invalid route USD values')
   expiry=datetime.fromisoformat(meta['fetched_utc'])+timedelta(seconds=30)
   if raw.get('expireAt') is not None:
    provider_expiry=datetime.fromisoformat(str(raw['expireAt']).replace('Z','+00:00'))
    if provider_expiry.tzinfo is None:raise Blocked('Unknown provider quote expiry zone')
    expiry=min(expiry,provider_expiry)
   q['expires_utc']=stamp(expiry)
   q['quote_id']=digest(q)
   return q
  except (KeyError,TypeError,ValueError,InvalidOperation):raise Blocked('Malformed quote response') from None
 @staticmethod
 def simulate(ticket,row,audit,quote,now):
  if not provenance_ok(row,now) or row['mint']!=ticket['mint'] or row['pair']!=ticket['pair']:
   raise Blocked('Stale/untrusted/wrong-identity market evidence')
  if not provenance_ok(quote,now,30) or not recent(quote.get('fetched_utc'),now,30):
   raise Blocked('Stale/unknown quote freshness')
  if (datetime.fromisoformat(quote['expires_utc'])-now).total_seconds()<=0:raise Blocked('Quote expired')
  if quote['quote_id']!=digest({k:v for k,v in quote.items() if k!='quote_id'}):raise Blocked('Quote hash mismatch')
  if any(quote[k]!=ticket[k] for k in ('mint','pair','side')) or quote['model']!=MODEL:
   raise Blocked('Quote identity/model mismatch')
  if quote['decimals']!=audit['decimals']:raise Blocked('Quote decimals mismatch')
  if dec(quote.get('slippage_pct'))!=dec(ticket['slippage_pct']):raise Blocked('Quote/request slippage mismatch')
  liquidity=dec(row.get('liquidity_usd'));mid=dec(row.get('price_usd'));slip=dec(ticket['slippage_pct'])
  if liquidity<10000 or mid<=0:raise Blocked('Mandatory liquidity/price evidence inadequate')
  # Route trade size is real depth-at-size evidence, NOT whole orderbook depth.
  buffer=Decimal('.0025');side=ticket['side']
  if side=='BUY':
   notional=money(ticket['usd'])
   if quote['input_mint']!=USDC or quote['output_mint']!=ticket['mint'] or int(quote['amount_atomic'])!=int(notional*1_000_000):
    raise Blocked('BUY quote binding mismatch')
   if abs(dec(quote['in_usd'])/notional-1)>Decimal('.005'):raise Blocked('USDC/USD assumption outside 0.5% bound')
   quantity=qty(dec(quote['output_atomic'])/(10**audit['decimals'])/(1+buffer))
   quantity=(quantity*(10**audit['decimals'])).to_integral_value(rounding=ROUND_DOWN)/(10**audit['decimals'])
   price=notional/quantity if quantity>0 else Decimal('0')
   adverse=max(Decimal('0'),price/mid-1)*100 if price else Decimal('999')
  else:
   quantity=qty(ticket['quantity'])
   if quote['input_mint']!=ticket['mint'] or quote['output_mint']!=USDC or int(quote['amount_atomic'])!=int(quantity*(10**audit['decimals'])):
    raise Blocked('SELL quote binding mismatch')
   if quantity*(10**audit['decimals'])!=int(quantity*(10**audit['decimals'])):raise Blocked('Quantity below mint precision')
   gross=dec(quote['output_atomic'])/1_000_000
   if abs(dec(quote['out_usd'])/gross-1)>Decimal('.005'):raise Blocked('USDC/USD assumption outside 0.5% bound')
   notional=money(min(gross,dec(quote['out_usd']))*(1-buffer))
   price=notional/quantity if quantity>0 else Decimal('0')
   adverse=max(Decimal('0'),1-price/mid)*100
  if quantity<=0 or notional<=0:raise Blocked('Zero simulated quantity/notional')
  if max(adverse,dec(quote['impact_pct'])+buffer*100)>slip:raise Blocked('Modeled adverse slippage exceeds approved cap')
  cap_value=notional if side=='BUY' else max(notional,quantity*mid)
  if cap_value>MAX_TRADE:raise Blocked('Maximum $2.50 notional per action exceeded')
  if cap_value>liquidity*Decimal('.001'):raise Blocked('Size exceeds 0.1% observed pool liquidity')
  # Explicit cost model; quote output already includes provider route fees. Additional
  # reserve deliberately overstates ancillary execution costs; never advertised as actual.
  fee=money(notional*Decimal('.003')+Decimal('.01'))
  if side=='SELL' and notional<=fee:raise Blocked('Sell proceeds do not cover modeled fees')
  return {'quantity':str(quantity),'notional':str(notional),'price':str(price),'fee':str(fee),
   'adverse_pct':str(adverse),'model':MODEL,'source_url':quote['url'],'quote_id':quote['quote_id'],
   'cost_assumption':'Route output plus adverse 25bp; additional 30bp + $0.01 estimated reserve',
   'chain_simulation':'NOT PERFORMED — local deterministic paper simulation only'}

class PaperLedger:
 """Separate additive event table; legacy observations/drafts/cash never become fills.
 Durable BEGIN IMMEDIATE transactions serialize approval consumption and fills.
 All monetary values/quantities are canonical decimal strings, not SQL REAL.
 """
 def __init__(self,path,clock=None):
  self.path=str(path);self.clock=clock or (lambda:datetime.now(timezone.utc))
  Path(path).parent.mkdir(parents=True,exist_ok=True)
  with self.db() as c:
   c.executescript('''
    CREATE TABLE IF NOT EXISTS paper_events_v1(
     seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
     utc TEXT NOT NULL, payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
    CREATE TRIGGER IF NOT EXISTS paper_events_no_update BEFORE UPDATE ON paper_events_v1
      BEGIN SELECT RAISE(ABORT,'paper ledger is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS paper_events_no_delete BEFORE DELETE ON paper_events_v1
      BEGIN SELECT RAISE(ABORT,'paper ledger is append-only'); END;
   ''')
   c.execute('BEGIN IMMEDIATE')
   if not c.execute('SELECT 1 FROM paper_events_v1 LIMIT 1').fetchone():
    self._append(c,'capital','capital',{'usd':'50','source':'owner-confirmed paper capital; no real funds'})
   self._load(c)
 @contextmanager
 def db(self):
  c=sqlite3.connect(self.path,timeout=15)
  try:
   c.execute('PRAGMA busy_timeout=15000');c.execute('PRAGMA synchronous=FULL')
   with c:yield c
  finally:c.close()
 def _append(self,c,eid,kind,payload):
  last=c.execute('SELECT seq,hash FROM paper_events_v1 ORDER BY seq DESC LIMIT 1').fetchone()
  seq=last[0]+1 if last else 1;prev=last[1] if last else '0'*64;t=stamp(self.clock())
  row={'seq':seq,'event_id':eid,'kind':kind,'utc':t,'payload':payload,'prev_hash':prev}
  h=digest(row)
  c.execute('INSERT INTO paper_events_v1 VALUES(?,?,?,?,?,?,?)',(seq,eid,kind,t,canonical(payload),prev,h))
 def _load(self,c):
  events=[];prev='0'*64
  for expected,r in enumerate(c.execute('SELECT * FROM paper_events_v1 ORDER BY seq'),1):
   seq,eid,kind,t,payload,previous,h=r
   try:p=json.loads(payload)
   except ValueError:raise Blocked('Ledger malformed JSON') from None
   if not isinstance(p,dict):raise Blocked('Ledger payload must be an object')
   row={'seq':seq,'event_id':eid,'kind':kind,'utc':t,'payload':p,'prev_hash':previous}
   if seq!=expected or previous!=prev or digest(row)!=h:raise Blocked('Ledger integrity failure; entries frozen')
   prev=h;events.append({**row,'hash':h})
  if not events or events[0]['kind']!='capital' or events[0]['payload'].get('usd')!='50':
   raise Blocked('Ledger capital genesis invalid')
  # Replay is the only balance/position authority; there is no mutable cache to trust.
  state={'cash':Decimal('0'),'fees':Decimal('0'),'realized':Decimal('0'),'positions':{},
   'proposals':{},'approvals':{},'withdrawn':set(),'fills':{},'halts':set(),'marks':{},'equity':[]}
  capital_count=0
  for e in events:
   p=e['payload'];kind=e['kind']
   if kind not in {'capital','proposal','approval','withdrawal','halt','mark','equity','order','fill'}:raise Blocked('Unknown paper event kind')
   if kind=='capital':state['cash']+=dec(p['usd']);capital_count+=1
   elif kind=='proposal':state['proposals'][p['ticket']['decision_id']]=p
   elif kind=='approval':state['approvals'][p['decision_id']]=p
   elif kind=='withdrawal':state['withdrawn'].add(p['decision_id'])
   elif kind=='halt':state['halts'].add(p['day'])
   elif kind=='mark':state['marks'][p['mint']]=p
   elif kind=='equity':state['equity'].append({**p,'utc':e['utc']})
   elif kind=='fill':
    did=p['decision_id']
    if did in state['fills']:raise Blocked('Duplicate fill in ledger')
    prop=state['proposals'].get(did);app=state['approvals'].get(did)
    if not prop or not app or did in state['withdrawn'] or p['ticket_hash']!=digest(prop['ticket']):
     raise Blocked('Fill approval reconciliation failure')
    if app['ticket_hash']!=p['ticket_hash']:raise Blocked('Fill binding reconciliation failure')
    t=prop['ticket'];mint=t['mint'];q=dec(p['quantity']);n=money(p['notional']);fee=money(p['fee'])
    if q<=0 or n<=0 or fee<0:raise Blocked('Invalid fill economics')
    pos=state['positions'].get(mint,{'quantity':Decimal('0'),'basis':Decimal('0'),'pair':t['pair']})
    if t['side']=='BUY':
     state['cash']-=n+fee;pos['quantity']+=q;pos['basis']+=n+fee
    elif t['side']=='SELL':
     if q>pos['quantity']:raise Blocked('Oversold position')
     basis=pos['basis'] if q==pos['quantity'] else money(pos['basis']*q/pos['quantity'])
     pos['quantity']-=q;pos['basis']-=basis;state['cash']+=n-fee
     pnl=n-fee-basis
     if money(p.get('realized'))!=money(pnl):raise Blocked('Realized P&L reconciliation failure')
     state['realized']+=pnl
    else:raise Blocked('Unknown fill side')
    state['positions'][mint]=pos;state['fees']+=fee;state['fills'][did]=p
    if state['cash']<0:raise Blocked('Negative cash in ledger')
  if capital_count!=1:raise Blocked('Duplicate seed capital')
  state['positions']={k:v for k,v in state['positions'].items() if v['quantity']>0}
  return events,state
 def snapshot(self):
  with self.db() as c:return self._load(c)
 def export(self,kind=None,fmt='jsonl'):
  events,_=self.snapshot();rows=[e for e in events if kind is None or e['kind']==kind]
  if fmt=='jsonl':return '\n'.join(canonical(e) for e in rows)
  out=io.StringIO();w=csv.DictWriter(out,fieldnames=['seq','event_id','kind','utc','payload','prev_hash','hash']);w.writeheader()
  for e in rows:w.writerow({**e,'payload':canonical(e['payload'])})
  return out.getvalue()
 def _valuation(self,state,now):
  holdings=Decimal('0');basis=Decimal('0');fresh=True;position_rows=[]
  for mint,pos in state['positions'].items():
   mark=state['marks'].get(mint);valid=False;value=None
   if mark and mark['pair']==pos['pair']:
    value=pos['quantity']*dec(mark['price_usd']);holdings+=value
    valid=provenance_ok(mark,now)
   fresh=fresh and valid;basis+=pos['basis']
   position_rows.append({'mint':mint,'pair':pos['pair'],'quantity':str(pos['quantity']),
    'basis_usd':str(pos['basis']),'mark_value_usd':str(money(value)) if value is not None else None,
    'unrealized_usd':str(money(value-pos['basis'])) if value is not None else None,
    'mark_fresh':valid,'mark_source':mark.get('url') if mark else None,
    'mark_fetched_utc':mark.get('fetched_utc') if mark else None})
  # Missing marks do not become zero-valued trustworthy equity.
  missing=any(p['mark_value_usd'] is None for p in position_rows)
  equity=None if missing else money(state['cash']+holdings)
  unreal=None if missing else money(holdings-basis)
  historical=[dec(e['net_equity']) for e in state['equity'] if e.get('fresh') and e.get('net_equity') is not None]
  peak=max([CAPITAL]+historical+([equity] if equity is not None and fresh else []))
  day=now.astimezone(TZ).date().isoformat()
  day_events=[e for e in state['equity'] if e['day']==day]
  prior=[e for e in state['equity'] if e['day']<day and e.get('fresh') and e.get('net_equity') is not None]
  baseline=dec(day_events[0]['baseline']) if day_events else max(CAPITAL,dec(prior[-1]['net_equity']) if prior else CAPITAL)
  daily=None if equity is None else money(equity-baseline)
  # Unrealized values include historical entry fees in basis; gross equity adds back all
  # fees charged so far. Exit cost estimate shown separately; not quietly netted twice.
  exit_reserve=money(sum((dec(p['mark_value_usd'] or 0)*Decimal('.003')+Decimal('.01') for p in position_rows),Decimal('0')))
  return {'cash':str(money(state['cash'])),'fees':str(money(state['fees'])),'realized':str(money(state['realized'])),
   'unrealized':str(unreal) if unreal is not None else None,'net_equity':str(equity) if equity is not None else None,
   'gross_equity_before_fees':str(money(equity+state['fees'])) if equity is not None else None,
   'estimated_exit_cost_reserve':str(exit_reserve),'fresh':fresh and not missing,'positions':position_rows,
   'day':day,'baseline':str(baseline),'daily_pnl':str(daily) if daily is not None else None,
   'daily_halted':day in state['halts'],'peak':str(peak),
   'drawdown_usd':str(money(max(Decimal('0'),peak-equity))) if equity is not None else None,
   'drawdown_pct':str(money(max(Decimal('0'),peak-equity)/peak*100)) if equity is not None and peak>0 else None}
 def portfolio(self):
  _,state=self.snapshot();return self._valuation(state,self.clock())
 def _record_equity(self,c,state,now):
  v=self._valuation(state,now)
  if v['fresh'] and v['daily_pnl'] is not None and dec(v['daily_pnl'])<=-DAILY_LOSS and v['day'] not in state['halts']:
   self._append(c,'halt:'+v['day'],'halt',{'day':v['day'],'reason':'Daily realized + unrealized loss ≥ $2.50','equity':v['net_equity']})
   v['daily_halted']=True
  self._append(c,'equity:'+uuid.uuid4().hex,'equity',v)
  return v
 def mark(self,rows):
  now=self.clock()
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');_,state=self._load(c)
   for row in rows:
    mint=row.get('mint');pos=state['positions'].get(mint)
    if not pos:continue
    if row.get('pair')!=pos['pair'] or not provenance_ok(row,now) or dec(row.get('price_usd'))<=0:
     raise Blocked('Invalid/stale/wrong-pair mark; prior marks retained')
    old=state['marks'].get(mint)
    if old and seconds(row['fetched_utc'],now)>seconds(old['fetched_utc'],now):raise Blocked('Mark cannot move backward in time')
    eid='mark:'+digest(row)
    if not c.execute('SELECT 1 FROM paper_events_v1 WHERE event_id=?',(eid,)).fetchone():self._append(c,eid,'mark',row)
    state['marks'][mint]=row
   return self._record_equity(c,state,now)

class PaperBroker:
 def __init__(self,ledger,gates=None,human_identity=None):
  self.ledger=ledger;self.gates=gates or DeskEvidence();self.human_identity=human_identity or (lambda:None)
 def _owner(self,gate):
  principal=self.human_identity()
  if not principal or principal!=gate.get('owner_identity_hash'):raise Blocked('Authenticated owner session missing/mismatched; no public visitor approval')
  return principal
 @staticmethod
 def validate_ticket(ticket):
  required={'decision_id','mint','pair','side','usd','quantity','slippage_pct','quote_id','quote_expires_utc','audit_id','rule_version'}
  if set(ticket)!=required:raise Blocked('Ticket fields missing or unexpected')
  if not re.fullmatch('[A-Za-z0-9_-]{8,100}',ticket['decision_id']):raise Blocked('Invalid decision id')
  if not mint_valid(ticket['mint']) or not mint_valid(ticket['pair']) or ticket['side'] not in ('BUY','SELL'):
   raise Blocked('Invalid exact ticket identity')
  if not 0<dec(ticket['slippage_pct'])<=MAX_SLIPPAGE:raise Blocked('Max slippage 3%')
  if ticket['rule_version']!=RULES:raise Blocked('Unknown/unpromoted rule')
  if ticket['side']=='BUY':
   if not 0<dec(ticket['usd'])<=MAX_TRADE or dec(ticket['quantity'])!=0:raise Blocked('BUY notional > $2.50 or invalid quantity')
   if dec(ticket['usd'])*1_000_000!=(dec(ticket['usd'])*1_000_000).to_integral_value():raise Blocked('USD size below USDC precision')
  elif dec(ticket['quantity'])<=0 or dec(ticket['usd'])!=0:raise Blocked('Invalid exact SELL quantity')
 def _checks(self,t,row,a,q,state,now):
  self.validate_ticket(t)
  gate=self.gates.read(now) # Re-read inside every approval and placement transaction.
  if a.get('mint')!=t['mint'] or a.get('audit_id')!=t['audit_id']:
   raise Blocked('Authority audit identity/version mismatch')
  if a.get('audit_id')!=digest({k:v for k,v in a.items() if k!='audit_id'}):raise Blocked('Audit hash mismatch')
  if not provenance_ok(a,now) or a.get('subset_verdict')!='PASS SUBSET':raise Blocked('Authority/tax evidence BLIND or FORBIDDEN')
  risk=gate.get('risk',{}).get(t['mint'],{})
  if risk.get('verdict')!='CLEAR' or risk.get('audit_id')!=a['audit_id'] or risk.get('pair')!=t['pair']:
   raise Blocked('Separate authoritative full RISK CLEAR missing/mismatched')
  if not all(risk.get(k) is True for k in ('holders_clear','social_clear','all_mandatory_checks_clear')):
   raise Blocked('Required holder/social/full risk evidence BLIND')
  if q.get('quote_id')!=t['quote_id'] or q.get('expires_utc')!=t['quote_expires_utc']:
   raise Blocked('Quote version/expiry mismatch')
  # Entry filter really executes; it never certifies profitability or full risk.
  if t['side']=='BUY' and (dec(row.get('liquidity_usd'))<10000 or dec(row.get('volume_h1_usd'))<1000):
   raise Blocked('Research entry thresholds not met')
  fill=RouteModel.simulate(t,row,a,q,now)
  v=self.ledger._valuation(state,now)
  if t['side']=='BUY':
   if not v['fresh']:raise Blocked('Open-position marks stale/unknown; equity not fresh')
   if v['daily_halted'] or (v['daily_pnl'] is not None and dec(v['daily_pnl'])<=-DAILY_LOSS):raise Blocked('Daily loss entry halt latched')
   pos=state['positions'].get(t['mint'])
   if not pos and len(state['positions'])>=MAX_POSITIONS:raise Blocked('Max 3 open positions')
   if pos and pos['pair']!=t['pair']:raise Blocked('Position pair mismatch')
   # Conservative owner size interpretation: no pyramiding over $2.50 cost basis.
   if pos and pos['basis']+dec(fill['notional'])>MAX_TRADE:raise Blocked('Per-mint exposure cap $2.50')
   if state['cash']<dec(fill['notional'])+dec(fill['fee']):raise Blocked('Insufficient paper cash including modeled fees')
  else:
   pos=state['positions'].get(t['mint'])
   if not pos or pos['pair']!=t['pair'] or dec(fill['quantity'])>pos['quantity']:raise Blocked('SELL exceeds held exact quantity/pair')
  return fill,gate
 def propose(self,ticket,row,audit,quote):
  self.validate_ticket(ticket)
  if quote.get('quote_id')!=ticket['quote_id'] or audit.get('audit_id')!=ticket['audit_id']:raise Blocked('Proposal evidence mismatch')
  p={'ticket':ticket,'market':row,'audit':audit,'quote':quote,'created_utc':stamp(self.ledger.clock()),
   'status':'PROPOSED / NOT APPROVED / NO FILL'}
  with self.ledger.db() as c:
   c.execute('BEGIN IMMEDIATE');_,state=self.ledger._load(c);did=ticket['decision_id']
   if did in state['proposals']:
    if state['proposals'][did]!=p:raise Blocked('Decision id already bound; never rebind intent')
    return did
   self.ledger._append(c,'proposal:'+did,'proposal',p)
  return did
 def diagnostics(self,did):
  _,state=self.ledger.snapshot()
  if did not in state['proposals']:return ['Proposal not found']
  p=state['proposals'][did]
  try:
   _,gate=self._checks(p['ticket'],p['market'],p['audit'],p['quote'],state,self.ledger.clock());self._owner(gate);return []
  except (Blocked,KeyError,TypeError,ValueError) as e:return [str(e)]
 def approve(self,did,exact_ticket_hash,human_confirmation):
  if human_confirmation!='CONFIRM PAPER '+did:raise Blocked('Exact manual confirmation text required')
  now=self.ledger.clock()
  with self.ledger.db() as c:
   c.execute('BEGIN IMMEDIATE');_,state=self.ledger._load(c)
   p=state['proposals'].get(did)
   if not p or digest(p['ticket'])!=exact_ticket_hash:raise Blocked('Approval exact ticket hash mismatch')
   if did in state['withdrawn'] or did in state['fills']:raise Blocked('Decision withdrawn/already used')
   _,gate=self._checks(p['ticket'],p['market'],p['audit'],p['quote'],state,now)
   principal=self._owner(gate)
   existing=state['approvals'].get(did)
   if existing:raise Blocked('Approval already issued; reconcile, do not extend or re-approve')
   app={'decision_id':did,'ticket_hash':exact_ticket_hash,'approved_by':'human:'+principal,
        'issued_utc':stamp(now),'expires_utc':p['quote']['expires_utc'],'approval_id':uuid.uuid4().hex}
   self.ledger._append(c,'approval:'+did,'approval',app)
   return app
 def withdraw(self,did):
  with self.ledger.db() as c:
   c.execute('BEGIN IMMEDIATE');_,s=self.ledger._load(c)
   if did not in s['proposals'] or did in s['fills']:raise Blocked('No withdrawable proposal')
   if did not in s['withdrawn']:self.ledger._append(c,'withdrawal:'+did,'withdrawal',{'decision_id':did})
 def place(self,did,approval_id,exact_ticket_hash):
  """Single local atomic paper send. On uncertain I/O caller must reconcile, never retry."""
  try:
   with self.ledger.db() as c:
    c.execute('BEGIN IMMEDIATE');_,state=self.ledger._load(c)
    p=state['proposals'].get(did);app=state['approvals'].get(did)
    if not p or digest(p['ticket'])!=exact_ticket_hash:raise Blocked('Placement ticket mismatch')
    if not app or app['approval_id']!=approval_id or app['ticket_hash']!=exact_ticket_hash:
     raise Blocked('Missing/mismatched exact approval')
    # Idempotent reconciliation returns the original result, never another fill.
    if did in state['fills']:return {**state['fills'][did],'reconciled_existing':True}
    if did in state['withdrawn']:raise Blocked('Approval withdrawn')
    now=self.ledger.clock()
    if not recent(app['issued_utc'],now,30) or seconds(app['expires_utc'],now)>=0:raise Blocked('Approval stale/expired')
    fill,gate=self._checks(p['ticket'],p['market'],p['audit'],p['quote'],state,now)
    if app['approved_by']!='human:'+self._owner(gate):raise Blocked('Approved owner identity mismatch')
    t=p['ticket'];realized=Decimal('0')
    if t['side']=='SELL':
     pos=state['positions'][t['mint']];q=dec(fill['quantity'])
     basis=pos['basis'] if q==pos['quantity'] else money(pos['basis']*q/pos['quantity'])
     realized=money(dec(fill['notional'])-dec(fill['fee'])-basis)
    # Recheck global evidence immediately before committing the local order batch.
    fill,gate=self._checks(t,p['market'],p['audit'],p['quote'],state,self.ledger.clock())
    if app['approved_by']!='human:'+self._owner(gate):raise Blocked('Owner session changed before commit')
    event={**fill,'decision_id':did,'mint':t['mint'],'pair':t['pair'],'side':t['side'],
     'ticket_hash':exact_ticket_hash,'approval_id':approval_id,'realized':str(realized),
     'gate_receipt':gate['evidence_id'],'gate_hash':digest(gate),'gate_evidence':gate,'utc':stamp(now)}
    self.ledger._append(c,'order:'+did,'order',{'decision_id':did,'ticket':t,'quote_id':fill['quote_id'],'mode':'PAPER ONLY'})
    self.ledger._append(c,'fill:'+did,'fill',event)
    # Entry mark is the genuine observed mark, not the modeled fill price.
    self.ledger._append(c,'entry-mark:'+did,'mark',p['market'])
    _,updated=self.ledger._load(c);self.ledger._record_equity(c,updated,now)
    return event
  except (sqlite3.Error,OSError):
   raise UnknownResult('UNKNOWN RESULT — reconcile by decision id; do not submit again') from None
 def reconcile(self,did):
  _,state=self.ledger.snapshot()
  if did in state['fills']:return {'status':'FILLED / PAPER','fill':state['fills'][did]}
  return {'status':'NO COMMITTED FILL FOUND — no retry; inspect integrity and create fresh approved decision only after resolution'}

def build_ticket(row,audit,quote,side,usd,quantity,slip,decision_id=None):
 return {'decision_id':decision_id or uuid.uuid4().hex,'mint':row['mint'],'pair':row['pair'],'side':side,
  'usd':str(dec(usd)),'quantity':str(dec(quantity)),'slippage_pct':str(dec(slip)),
  'quote_id':quote['quote_id'],'quote_expires_utc':quote['expires_utc'],'audit_id':audit['audit_id'],'rule_version':RULES}

def run_ui():
 import streamlit as st
 import pandas as pd
 import plotly.graph_objects as go
 from html import escape
 st.set_page_config(page_title='PumpGrok | Paper System v3',page_icon='◈',layout='wide')
 base=Path(__file__).parent
 db=Path(os.environ.get('PUMPGROK_TERMINAL_DB',str(base/'terminal_data/terminal.sqlite3')))
 research=ResearchStore(db)
 def ui_fetch(url,body=None):
  provider='dexscreener' if url.startswith(API+'/') else ('solana-rpc' if url==RPC else 'jupiter')
  if research.get('source_stopped:'+provider,False):raise ProviderError(provider+' access previously denied; stopped, no retries or alternate route')
  try:return public_json(url,body)
  except ProviderError as e:
   if any(code in str(e) for code in ('401','403','451','Redirect','denied','blocked')):research.set('source_stopped:'+provider,True)
   raise
 try:
  ledger=PaperLedger(db)
  def owner_identity():
   # Only verified OIDC claims; no token, credential or contact-detail reads/logging.
   try:
    if not st.user.get('is_logged_in',False):return None
    iss=st.user.get('iss');sub=st.user.get('sub');now=ledger.clock().timestamp()
    if not iss or not sub or iss!=os.environ.get('PUMPGROK_OWNER_ISSUER') or sub!=os.environ.get('PUMPGROK_OWNER_SUBJECT'):return None
    if not float(st.user.get('iat',float('inf')))<=now<float(st.user.get('exp',0)):return None
    if float(st.user.get('nbf',0))>now:return None
    return digest({'issuer':iss,'subject':sub})
   except (AttributeError,TypeError,ValueError):return None
  broker=PaperBroker(ledger,human_identity=owner_identity);events,state=ledger.snapshot();v=ledger.portfolio()
 except (Blocked,sqlite3.Error,OSError) as e:
  st.error('LEDGER INTEGRITY / STORAGE FAILURE — ALL ACTIONS STOPPED: '+str(e));st.stop()
 def english(x):
  if isinstance(x,str) and re.search('[\u0980-\u09ff]',x):return 'Localized source text hidden; original evidence preserved.'
  if isinstance(x,dict):return {english(k):english(val) for k,val in x.items()}
  if isinstance(x,list):return [english(val) for val in x]
  return x
 def table(rows):
  if not rows:st.caption('No records yet.');return
  st.dataframe(pd.DataFrame(english(rows)),hide_index=True,width='stretch')
 def html(value):st.markdown(value,unsafe_allow_html=True)
 def amount(x):return 'UNKNOWN' if x is None else f'${dec(x):,.2f}'
 def notify(f):
  try:
   result=f();st.success('Request finished. See exact evidence below.');return result
  except (Blocked,ProviderError,UnknownResult,sqlite3.Error,ValueError,KeyError,TypeError) as e:
   research.log('CODE / BLOCKED',str(e));st.error(str(e));return None

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
 
 html('<div class="header"><div><div class="brand"><span class="brand-icon">◈</span><b>PumpGrok</b> Paper System</div><div class="version">Paper System v3 • English / Dark • Single File</div></div><div class="chips"><span class="chip cyan">REAL MARKET READS</span><span class="chip">SIMULATED ORDERS ONLY</span><span class="chip amber">MANUAL APPROVAL</span></div></div>')
 bridge=None
 try:
  bridge=broker.gates.read(ledger.clock());gate_status='VERIFIED PAPER GATES / '+bridge['evidence_id']
 except Blocked as e:gate_status=str(e)
 st.warning(gate_status)
 st.caption('No wallets, real orders, autonomous schedules or connected assistant Bots. Local paper engine code is implemented; external clearance is never inferred from a missing halt file.')
 metrics=st.columns(6)
 for col,label,val in zip(metrics,['Paper Cash','Net Equity (indicative MTM)','Realized P&L','Unrealized P&L','Modeled Fees Paid','Open Positions'],
  [amount(v['cash']),amount(v['net_equity']),amount(v['realized']),amount(v['unrealized']),amount(v['fees']),str(len(v['positions']))]):col.metric(label,val)
 if not v['fresh']:st.error('MARKS STALE / UNKNOWN — equity not fresh; new entries blocked. Last-known marks are not current performance.')
 rail,body=st.columns([1,3],gap='large')
 with rail:
  html('<div class="section">ASSISTANT BOT STATUS / 10 SEATS</div>')
  for role,description in ROLES.items():html(f'<div class="seat"><b>{role}</b><span>NOT CONNECTED</span><p>{escape(description)}</p></div>')
  st.caption('Role mapping describes intended responsibilities. Code stages are not messages or work from these Bots.')
  st.metric('Observed Pairs',len(research.rows()))
  st.metric('Confirmed Rugs Blocked',0,help='Unknown evidence is BLIND, never proof of a rug. No full RISK integration exists.')
  st.caption('Asia/Dhaka (UTC+6) daily boundaries; evidence timestamps stored in UTC. No background trading.')
 with body:
  overview,scanner,positions,tickets,logs,safety=st.tabs(['Overview','Scanner','Positions','Paper Tickets / Approvals','Ledger / Activity','Safety / Config'])
  with overview:
   html('<div class="state"><div class="eyebrow">CURRENT CODE STATE / NO BACKGROUND WORK</div><h2>Manual research → quote → exact approval → paper fill</h2><p>Scanner reads real markets. Authority audit reads finalized RPC data. Quote reads an informational route. The local broker simulates adverse execution only after every verified desk gate passes.</p><div class="next">Next: scan a real pair, inspect evidence and the exact lock reasons. No paper fill can bypass the global halt, unknown desk status, unpromoted rules or missing full RISK clearance.</div></div>')
   table([{'Daily P&L':amount(v['daily_pnl']),'Daily baseline':amount(v['baseline']),'Peak-to-current drawdown':amount(v['drawdown_usd']),
    'Drawdown %':v['drawdown_pct'],'Daily entry halt latched':v['daily_halted'],'Equity marks fresh':v['fresh']}])
   curve=[{'utc':events[0]['utc'],'equity':50.0}]+[{'utc':e['utc'],'equity':float(e['payload']['net_equity'])} for e in events if e['kind']=='equity' and e['payload'].get('fresh') and e['payload'].get('net_equity') is not None]
   fig=go.Figure(go.Scatter(x=[r['utc'] for r in curve],y=[r['equity'] for r in curve],mode='lines+markers',line=dict(color='#45d9b3'),fill='tozeroy'))
   fig.update_layout(template='plotly_dark',height=250,paper_bgcolor='#0e1727',plot_bgcolor='#0e1727',yaxis_title='Paper USD',yaxis_rangemode='normal',margin=dict(l=10,r=10,t=10,b=20))
   st.plotly_chart(fig,width='stretch')
   st.caption('Only committed fresh-mark valuations appear. Initial $50 is capital, not profit. Indicative MTM is not liquidation equity; estimated remaining exit-cost reserve: '+amount(v['estimated_exit_cost_reserve']))
   st.info('No automatic profit claims. Entry thresholds and proposed stop/take-profit are unproven research rules. Replay and owner promotion are required before any paper ticket can be approved.')
  with scanner:
   st.subheader('Real Market Scanner')
   stage=st.empty()
   if st.button('Run Scanner Cycle',type='primary'):
    def progress(s,m):stage.info(s+' — '+m)
    result=scan(research,fetch=lambda path:ui_fetch(API+path),progress=progress);st.session_state['last_scan']=result
   health=research.get('health',{})
   st.write('Provider: DexScreener / '+health.get('status','NOT FETCHED'))
   if st.session_state.get('last_scan'):st.caption(st.session_state['last_scan']['message'])
   if health.get('error'):st.error(health['error'])
   rows=research.rows()
   table([{'Symbol':english(r['symbol']),'Mint':r['mint'],'Pair':r['pair'],'Indicative USD':r['price_usd'],
    'Liquidity USD':r['liquidity_usd'],'Volume 1h USD':r['volume_h1_usd'],
    'Retrieval Age Seconds':round(age(r['fetched_utc']),1),'Source Market Time':'UNKNOWN',
    'HTTP Age':r.get('http_age'),'Retrieval / Cache Validation':'VALID' if provenance_ok(r,ledger.clock()) else 'STALE / UNKNOWN','Source':r['url']} for r in rows])
   st.caption('Latest profiles are not all market launches. Retrieval time is not provider market time. HTTP age/date are validated again at approval. No synthetic fallback. Shared 30-second discovery cooldown.')
   if rows:
    options=list(range(len(rows)));index=st.selectbox('Exact Pair',options,format_func=lambda i:english(rows[i]['symbol'])+' | '+rows[i]['pair'])
    selected=rows[index];mint=selected['mint'];pair=selected['pair']
    st.json(candidate(selected))
    if st.button('Refresh Selected Mint — Real Read Only'):
     def refresh_selected():
      if age(research.get('selected_refresh_attempt'))<10:raise Blocked('Shared 10-second market refresh cooldown')
      research.set('selected_refresh_attempt',utc());return read_market(mint,ui_fetch)
     result=notify(refresh_selected)
     if result:research.save_rows(result);research.log('CODE / MARKET','Refreshed exact mint '+mint);st.rerun()
    if st.button('Read Authority / Token-2022 Evidence'):
     def do_audit():
      if research.get('rpc_stopped'):raise Blocked('RPC stopped after denial; provider/operator resolution required')
      if age(research.get('rpc_attempt'))<2:raise Blocked('RPC 2-second read budget cooldown')
      research.set('rpc_attempt',utc())
      try:a=read_authority(mint,ui_fetch)
      except ProviderError as e:
       if any(x in str(e) for x in ('403','451','denied','blocked')):research.set('rpc_stopped',True)
       raise
      research.set('audit:'+mint,a);research.log('CODE / AUDIT',a['subset_verdict']+' for '+mint+'; separate full RISK clearance still required');return a
     notify(do_audit)
    a=research.get('audit:'+mint)
    if a:st.json(english(a))
    else:st.warning('Authority/extension evidence BLIND. Read-only audit is not a full RISK Bot audit.')
    st.subheader('Prepare Exact Paper Proposal — No Fill')
    with st.form('prepare'):
     side=st.selectbox('Side',['BUY','SELL'])
     usd=st.number_input('BUY notional USD (SELL uses exact quantity)',min_value=.01,max_value=2.5,value=2.5,step=.01)
     quantity=st.text_input('SELL exact token quantity','0')
     slip=st.number_input('Maximum slippage % (cap, not an assumed fixed loss)',min_value=.01,max_value=3.0,value=3.0,step=.1)
     prepare=st.form_submit_button('Read Route Quote / Save Exact Proposal')
    if prepare:
     def do_prepare():
      if not a or a['subset_verdict']!='PASS SUBSET' or not provenance_ok(a,ledger.clock()):raise Blocked('Fresh passing authority/tax subset required before quote')
      if research.get('quote_stopped'):raise Blocked('Quote provider stopped after denial; no alternate route')
      if age(research.get('quote_attempt'))<3:raise Blocked('Quote 3-second shared read cooldown')
      seed={'mint':mint,'pair':pair,'side':side,'usd':str(usd if side=='BUY' else 0),
       'quantity':quantity if side=='SELL' else '0','slippage_pct':str(slip)}
      research.set('quote_attempt',utc())
      try:q=RouteModel.request(seed,a,ui_fetch)
      except ProviderError as e:
       if any(x in str(e) for x in ('401','403','451','denied','blocked')):research.set('quote_stopped',True)
       raise
      ticket=build_ticket(selected,a,q,side,seed['usd'],seed['quantity'],slip)
      did=broker.propose(ticket,selected,a,q)
      research.log('CODE / PROPOSAL','Exact paper proposal '+did+' saved; no approval or fill.');return did
     did=notify(do_prepare)
     if did:st.session_state['selected_decision']=did;st.success('Proposal '+did+' saved. Inspect Paper Tickets / Approvals immediately; quote expires in 30 seconds.')
    with st.expander('Original Market Evidence'):st.json(english(selected))
  with positions:
   st.subheader('Durable Paper Positions')
   table(v['positions'])
   if st.button('Refresh Open-Position Markets / Record Marks'):
    def do_marks():
     if age(research.get('mark_attempt'))<10:raise Blocked('Shared 10-second mark read cooldown')
     research.set('mark_attempt',utc());all_rows=[]
     for mint,pos in state['positions'].items():
      rows=read_market(mint,ui_fetch);matches=[r for r in rows if r['pair']==pos['pair']]
      if not matches:raise Blocked('Held pair not returned; marks remain stale')
      all_rows.append(matches[0])
     return ledger.mark(all_rows)
    result=notify(do_marks)
    if result:st.json(result)
   st.caption('SELL requires a new future fresh quote, exact quantity and fresh manual approval. Partial exits track weighted average basis. No random or immediate fabricated exits; each sell action is capped at $2.50.')
  with tickets:
   st.subheader('Exact Manual Paper Approvals')
   if not owner_identity():
    st.caption('Authenticated owner identity is required for approval and placement. Read-only research stays available.')
    if st.button('Owner Sign-In — Requires Configured OIDC'):
     try:st.login()
     except Exception:st.error('Owner OIDC is not configured or unavailable. Owner-authorized authentication setup is required; no credentials are requested or logged here.')
   if st.session_state.get('paper_notice'):st.info(st.session_state.pop('paper_notice'))
   _,current_state=ledger.snapshot();proposals=current_state['proposals']
   if not proposals:st.caption('No paper proposals. Scan, audit, and read a real route quote first.')
   else:
    did=st.selectbox('Decision ID',list(reversed(proposals)),key='proposal_choice')
    p=proposals[did];t=p['ticket'];st.json(english(t))
    st.caption('Binding hash: '+digest(t)+' · quote expires UTC: '+t['quote_expires_utc'])
    reasons=broker.diagnostics(did)
    if reasons:
     for reason in reasons:st.error('NO FILL: '+reason)
    else:st.success('Current verified checks pass; exact manual confirmation is still required.')
    with st.expander('Quote / Audit / Market Evidence'):st.json(english(p))
    confirmation=st.text_input('Type CONFIRM PAPER '+did,value='',key='confirm:'+did)
    if st.button('Approve Exact Paper Ticket',disabled=bool(reasons)):
     app=notify(lambda:broker.approve(did,digest(t),confirmation))
     if app:st.session_state['paper_notice']='Exact approval saved. Place is a separate explicit action.';st.rerun()
    app=current_state['approvals'].get(did)
    if app:st.json(app)
    if st.button('Place Approved Simulated Order ONCE',disabled=bool(reasons) or not app or did in current_state['fills'] or did in current_state['withdrawn']):
     result=notify(lambda:broker.place(did,app['approval_id'],digest(t)))
     if result:st.session_state['paper_notice']='Simulated fill committed once. Inspect Positions / Ledger.';st.rerun()
    if st.button('Withdraw Unfilled Decision',disabled=did in current_state['fills']):notify(lambda:broker.withdraw(did))
    if st.button('Reconcile Decision — Read Only'):st.json(broker.reconcile(did))
   st.caption('No checkbox can clear the desk. Approval binds mint, pair, side, amount, quantity, slippage, quote hash/expiry, authority audit, rule version and decision id. No extension of expired approvals. UNKNOWN RESULT means reconcile; never resubmit.')
  with logs:
   st.subheader('Trade Log — Committed Paper Fills Only')
   table([e['payload'] for e in events if e['kind']=='fill'])
   st.subheader('Code Activity — Not Agent Activity')
   table([{'UTC':e['utc'],'Code Stage':e['stage'],'Actual action / findings':english(e['message'])} for e in research.events()])
   with st.expander('Append-only Paper Event Ledger / Hashes'):
    table([{'Seq':e['seq'],'UTC':e['utc'],'Kind':e['kind'],'ID':e['event_id'],'Hash':e['hash'],'Payload':canonical(english(e['payload']))} for e in events])
   st.caption('Startup verifies contiguous sequence, hash chain and replayed balances/approvals/basis. Export includes UTC timestamps, source URLs and quote provenance where relevant.')
   for kind,label in [(None,'All Events'),('order','Orders'),('approval','Approvals'),('fill','Fills'),('equity','Equity'),('mark','Marks')]:
    c1,c2=st.columns(2)
    with c1:st.download_button(label+' CSV',ledger.export(kind,'csv'),file_name=(kind or 'events')+'.csv',mime='text/csv',key='csv:'+str(kind))
    with c2:st.download_button(label+' JSONL',ledger.export(kind),file_name=(kind or 'events')+'.jsonl',mime='application/x-ndjson',key='jsonl:'+str(kind))
   st.download_button('Drawdown / Portfolio Summary JSON',canonical(v),file_name='portfolio-summary.json',mime='application/json')
  with safety:
   st.json(POLICY);st.write('Gate state: '+gate_status)
   st.json({'Actual global kill':'ACTIVE' if KILL_PATH.exists() else 'ABSENT / NOT PROOF OF CLEARANCE',
    'Authoritative desk status':'VERIFIED SHORT-LIVED SIGNATURE' if bridge else 'UNKNOWN / NOT CONNECTED',
    'Effective policy':'VERIFIED AGAINST OWNER LIMITS' if bridge else 'UNVERIFIED / REPORTED LEGACY MISMATCH NOT RESOLVED',
    'Rules and model promotion':'VERIFIED RECEIPT' if bridge else 'NOT VERIFIED / RESEARCH ONLY',
    'Full RISK Bot verdict':'Per-ticket signed evidence required; code audit alone is never CLEAR',
    'Owner approval session':'VERIFIED' if owner_identity() else 'UNAUTHENTICATED / NOT CONFIGURED',
    'Assistant integrations':'ALL 10 NOT CONNECTED','Order implementation':'LOCAL MODELED PAPER BROKER; NO LIVE ORDER ENDPOINTS'})
   st.write('Persistence path: '+str(db));st.write('Ledger hash-chain and replay: VERIFIED at this request')
   st.warning('Streamlit Cloud local disk is ephemeral. Configure PUMPGROK_TERMINAL_DB to a durable mounted volume on a suitable host, and export/back up the ledger. No hosted database integration is configured. Losing the file loses approvals, loss latches and history; never describe Cloud local storage as durable production custody.')
   st.write('Activation prerequisites: owner-authorized sanctioned desk bridge; actual halt CLEAR through owner procedure; effective policy agreement; fresh signed full RISK clearance for this mint/audit/pair; recorded replay and human rule/model promotion; fresh real market/RPC/route evidence; exact manual approval. This app does not clear the halt or write desk policy.')
   st.caption('Signed bridge interface is implemented, but no upstream bridge is installed. Public verification key + fresh signed attestation are provisioned only after owner approval. A missing file or a user-supplied unsigned JSON is never clearance. All 10 actual assistants remain disconnected.')
   st.caption('Route model: genuine Jupiter informational quote without taker, adverse 25bp buffer, extra modeled 30bp + $0.01 cost reserve. No on-chain transaction simulation. USDC/USD deviation over 0.5%, missing fees, route, liquidity, stale evidence or unsafe authorities reject the order.')
   st.caption('Daily loss: net equity versus prior recorded fresh daily close, with conservative $50 minimum baseline; $2.50 loss latches new entries for that Asia/Dhaka day. No reset button. Marks are manually sampled, not guaranteed midnight prices; no continuous risk monitor is running. Exits require all global and risk gates even during a daily entry halt.')
   st.link_button('DexScreener docs',DOCS);st.link_button('Solana RPC docs','https://solana.com/docs/rpc/http/getaccountinfo')
   st.link_button('Jupiter quote-only docs','https://dev.jup.ag/api-reference/swap/v2/order')
 html('<div class="foot">PAPER SYSTEM V3 / ENGLISH / DARK / SINGLE FILE · REAL READS / MODELED PAPER EXECUTION<br>No guaranteed profit. No real money. No connected assistant Bots. No unattended trading.</div>')

if __name__=='__main__':run_ui()
