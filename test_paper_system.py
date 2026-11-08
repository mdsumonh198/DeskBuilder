"""TEST ONLY: engineered deterministic provider fixtures, NOT recorded performance.
Every ledger and non-wallet attestation test signer lives in a TemporaryDirectory.
Never imports/modifies the PumpGrok repository or its real halt/policy.
"""
import sys
import unittest
import tempfile
import json
import base64
import copy
import sqlite3
from pathlib import Path
from datetime import datetime,timezone,timedelta
from email.utils import format_datetime
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import trading_terminal as m
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

MINT='So11111111111111111111111111111111111111112'
PAIR='11111111111111111111111111111111'
M2='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
M3='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
M4='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'

class Fixture:
 def __init__(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='PAPER_TEST_ONLY_');self.root=Path(self.tmp.name)
  self.now=datetime(2026,11,8,20,0,tzinfo=timezone.utc)
  self.ledger=m.PaperLedger(self.root/'TEST_ONLY.sqlite',lambda:self.now)
  # NON-WALLET signature fixture: verifies the production attestation verifier only.
  self.signer=Ed25519PrivateKey.generate();pub=self.signer.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
  self.path=self.root/'TEST_ONLY_attestation.json';self.kill=self.root/'TEST_ONLY_KILL'
  self.gates=m.DeskEvidence(str(self.path),pub,self.kill);self.broker=m.PaperBroker(self.ledger,self.gates,human_identity=lambda:'a'*64)
  self.risks={};self.serial=0
 def meta(self,url):return {'url':url,'fetched_utc':m.stamp(self.now),'http_date':format_datetime(self.now,usegmt=True),'http_age':'0','provider_observation_utc':None}
 def row(self,price='1',mint=MINT):
  return {'mint':mint,'pair':PAIR,'symbol':'TEST_ONLY','price_usd':price,'liquidity_usd':'100000',
   'volume_h1_usd':'20000',**self.meta(m.API+'/tokens/v1/solana/'+mint)}
 def raw_authority(self,owner=m.SPL,extensions=None):
  info={'mintAuthority':None,'freezeAuthority':None,'isInitialized':True,'supply':'100000000000','decimals':6}
  if extensions is not None:info['extensions']=extensions
  return {'jsonrpc':'2.0','id':1,'result':{'context':{'slot':12345},'value':{'owner':owner,'executable':False,
   'data':{'program':'spl-token' if owner==m.SPL else 'spl-token-2022','space':82 if extensions is None else 400,
   'parsed':{'type':'mint','info':info}}}}}
 def audit(self,mint=MINT,raw=None):
  return m.parse_authority(raw or self.raw_authority(),mint,self.meta(m.RPC))
 def sign(self,modify=None):
  p={'audience':'pumpgrok-standalone-paper-v3','issued_utc':m.stamp(self.now),
   'expires_utc':m.stamp(self.now+timedelta(seconds=55)),'halt':'CLEAR','authoritative':True,
   'policy':copy.deepcopy(m.POLICY),'strategy':{'version':m.RULES,'replay_passed':True,'human_promoted':True,'model':m.MODEL},
   'owner_identity_hash':'a'*64,'risk':self.risks,'evidence_id':'TEST_ONLY_RECEIPT','owner_authorization_id':'TEST_ONLY_AUTHORIZATION'}
  if modify:modify(p)
  self.path.write_text(json.dumps({'payload':p,'signature':base64.b64encode(self.signer.sign(m.canonical(p).encode())).decode()}))
  return p
 def proposal(self,side='BUY',usd='2.5',quantity='0',price='1',mint=MINT,slip='3',out=None):
  self.serial+=1;row=self.row(price,mint);audit=self.audit(mint)
  seed={'mint':mint,'pair':PAIR,'side':side,'usd':usd if side=='BUY' else '0','quantity':quantity if side=='SELL' else '0','slippage_pct':slip}
  amount=int(D(usd)*1_000_000) if side=='BUY' else int(D(quantity)*1_000_000)
  out_amount=out if out is not None else (int(D(usd)/D(price)*1_000_000) if side=='BUY' else int(D(quantity)*D(price)*1_000_000))
  im=m.USDC if side=='BUY' else mint;om=mint if side=='BUY' else m.USDC
  raw={'inputMint':im,'outputMint':om,'inAmount':str(amount),'outAmount':str(out_amount),
   'swapMode':'ExactIn','slippageBps':int(D(slip)*100),'priceImpact':'0.01','feeBps':2,
   'signatureFeeLamports':0,'prioritizationFeeLamports':0,'rentFeeLamports':0,'requestId':'TEST_ONLY_'+str(self.serial),
   'transaction':None,'taker':None,'inUsdValue':usd if side=='BUY' else str(D(quantity)*D(price)),
   'outUsdValue':str(D(out_amount)/1_000_000*D(price)) if side=='BUY' else str(D(out_amount)/1_000_000),
   'routePlan':[{'percent':100,'bps':10000,'swapInfo':{'ammKey':PAIR,'inputMint':im,'outputMint':om,'inAmount':str(amount),'outAmount':str(out_amount)}}]}
  q=m.RouteModel.parse(raw,self.meta(m.JUP+'?TEST_ONLY=1'),seed,audit,amount,im,om)
  t=m.build_ticket(row,audit,q,side,seed['usd'],seed['quantity'],slip,'TEST_ONLY_'+str(self.serial))
  self.risks[mint]={'pair':PAIR,'audit_id':audit['audit_id'],'verdict':'CLEAR','holders_clear':True,'social_clear':True,'all_mandatory_checks_clear':True}
  self.sign();self.broker.propose(t,row,audit,q)
  return t,row,audit,q,raw
 def approve(self,t):return self.broker.approve(t['decision_id'],m.digest(t),'CONFIRM PAPER '+t['decision_id'])
 def fill(self,t):
  a=self.approve(t);return self.broker.place(t['decision_id'],a['approval_id'],m.digest(t))
 def cleanup(self):self.tmp.cleanup()

class EngineTests(unittest.TestCase):
 def setUp(self):self.f=Fixture()
 def tearDown(self):self.f.cleanup()
 def test_initial_capital_no_seed_profit(self):
  v=self.f.ledger.portfolio();self.assertEqual(D(v['cash']),50);self.assertEqual(D(v['net_equity']),50)
  self.assertEqual(D(v['realized']),0);self.assertEqual(D(v['unrealized']),0);self.assertEqual(len(self.f.ledger.snapshot()[0]),1)
 def test_buy_actual_valid_simulated_path(self):
  t,*_=self.f.proposal();fill=self.f.fill(t);v=self.f.ledger.portfolio()
  self.assertEqual(D(v['cash']),D('50')-D(fill['notional'])-D(fill['fee']))
  self.assertEqual(D(v['fees']),D('.0175'));self.assertEqual(len(v['positions']),1)
  self.assertLess(D(v['net_equity']),50);self.assertEqual(D(v['realized']),0)
 def test_partial_and_full_future_exit_basis_pnl(self):
  t,*_=self.f.proposal();buy=self.f.fill(t);self.f.now+=timedelta(seconds=5)
  self.f.ledger.mark([self.f.row('1.2')])
  sell,*_=self.f.proposal('SELL',quantity='1',price='1.2');one=self.f.fill(sell)
  basis=m.money((D(buy['notional'])+D(buy['fee']))/D(buy['quantity']))
  self.assertEqual(D(one['realized']),D(one['notional'])-D(one['fee'])-basis)
  remaining=self.f.ledger.portfolio()['positions'][0]['quantity'];self.f.now+=timedelta(seconds=5)
  sell2,*_=self.f.proposal('SELL',quantity=remaining,price='1.2');two=self.f.fill(sell2)
  v=self.f.ledger.portfolio();self.assertEqual(v['positions'],[])
  self.assertEqual(D(v['cash'])-50,D(v['realized']));self.assertEqual(D(v['unrealized']),0)
  self.assertEqual(len(self.f.ledger.snapshot()[1]['fills']),3)
 def test_restart_and_idempotence(self):
  t,*_=self.f.proposal();app=self.f.approve(t);fill=self.f.broker.place(t['decision_id'],app['approval_id'],m.digest(t))
  restarted=m.PaperBroker(m.PaperLedger(self.f.ledger.path,lambda:self.f.now),self.f.gates)
  old=restarted.place(t['decision_id'],app['approval_id'],m.digest(t));self.assertTrue(old['reconciled_existing'])
  self.assertEqual(fill['quantity'],old['quantity']);self.assertEqual(len(restarted.ledger.snapshot()[1]['fills']),1)
 def test_concurrent_single_fill(self):
  t,*_=self.f.proposal();a=self.f.approve(t)
  def do(_):return self.f.broker.place(t['decision_id'],a['approval_id'],m.digest(t))
  with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(do,range(8)))
  self.assertEqual(len(self.f.ledger.snapshot()[1]['fills']),1)
  self.assertEqual(sum(not x.get('reconciled_existing',False) for x in results),1)
 def test_missing_approval(self):
  t,*_=self.f.proposal()
  with self.assertRaises(m.Blocked):self.f.broker.place(t['decision_id'],'none',m.digest(t))
 def test_wrong_hash_confirmation_and_approval_id(self):
  t,*_=self.f.proposal()
  with self.assertRaises(m.Blocked):self.f.broker.approve(t['decision_id'],'wrong','CONFIRM PAPER '+t['decision_id'])
  with self.assertRaises(m.Blocked):self.f.broker.approve(t['decision_id'],m.digest(t),'yes')
  app=self.f.approve(t)
  with self.assertRaises(m.Blocked):self.f.broker.place(t['decision_id'],'wrong',m.digest(t))
  changed=dict(t,usd='2')
  with self.assertRaises(m.Blocked):self.f.broker.place(t['decision_id'],app['approval_id'],m.digest(changed))
 def test_expired_approval_and_quote(self):
  t,*_=self.f.proposal();a=self.f.approve(t);self.f.now+=timedelta(seconds=31);self.f.sign()
  with self.assertRaises(m.Blocked):self.f.broker.place(t['decision_id'],a['approval_id'],m.digest(t))
 def test_no_approval_extension(self):
  t,*_=self.f.proposal();self.f.approve(t)
  with self.assertRaises(m.Blocked):self.f.approve(t)
 def test_withdrawn_before_and_after_approval(self):
  t,*_=self.f.proposal();a=self.f.approve(t);self.f.broker.withdraw(t['decision_id'])
  with self.assertRaises(m.Blocked):self.f.broker.place(t['decision_id'],a['approval_id'],m.digest(t))
  t,*_=self.f.proposal();self.f.broker.withdraw(t['decision_id'])
  with self.assertRaises(m.Blocked):self.f.approve(t)
 def test_decision_rebinding(self):
  t,row,a,q,_=self.f.proposal()
  with self.assertRaises(m.Blocked):self.f.broker.propose(dict(t,usd='1'),row,a,q)
 def test_global_kill_wins_even_signed_clear(self):
  t,*_=self.f.proposal();app=self.f.approve(t);self.f.kill.write_text('TEST_ONLY_HALT')
  with self.assertRaisesRegex(m.Blocked,'GLOBAL KILL'):self.f.broker.place(t['decision_id'],app['approval_id'],m.digest(t))
 def test_unknown_cloud_status(self):
  gate=m.DeskEvidence(kill_path=self.f.root/'absent')
  with self.assertRaisesRegex(m.Blocked,'UNKNOWN'):gate.read(self.f.now)
 def test_signed_config_mismatch(self):
  t,*_=self.f.proposal();self.f.sign(lambda p:p['policy'].update(max_trade_usd='10'))
  with self.assertRaisesRegex(m.Blocked,'policy'):self.f.approve(t)
 def test_unsigned_and_tampered_attestation(self):
  self.f.sign();j=json.loads(self.f.path.read_text());j['payload']['halt']='CLEARER';self.f.path.write_text(json.dumps(j))
  with self.assertRaises(m.Blocked):self.f.gates.read(self.f.now)
 def test_attestation_stale_future_expired_wrong_audience(self):
  for mutate in [lambda p:p.update(issued_utc=m.stamp(self.f.now-timedelta(seconds=31))),
                 lambda p:p.update(issued_utc=m.stamp(self.f.now+timedelta(seconds=1))),
                 lambda p:p.update(expires_utc=m.stamp(self.f.now)),lambda p:p.update(audience='other')]:
   self.f.sign(mutate)
   with self.assertRaises(m.Blocked):self.f.gates.read(self.f.now)
 def test_unpromoted_strategy(self):
  t,*_=self.f.proposal();self.f.sign(lambda p:p['strategy'].update(human_promoted=False))
  with self.assertRaisesRegex(m.Blocked,'promoted'):self.f.approve(t)
 def test_missing_full_risk_or_holder_social(self):
  for key in ['verdict','holders_clear','social_clear','all_mandatory_checks_clear','audit_id','pair']:
   t,*_=self.f.proposal();self.f.sign(lambda p:p['risk'][MINT].pop(key,None))
   with self.assertRaises(m.Blocked):self.f.approve(t)
 def test_max_size_and_slippage_edges(self):
  for usd,slip in [('2.500001','3'),('0','3'),('-1','3'),('1','3.01'),('1','0'),('NaN','3'),('1','Infinity')]:
   t,*_=self.f.proposal()
   with self.assertRaises(m.Blocked):self.f.broker.validate_ticket(dict(t,usd=usd,slippage_pct=slip))
  t,*_=self.f.proposal(usd='.01',slip='3');self.f.fill(t)
 def test_slippage_rejected_not_fixed_3percent_loss(self):
  t,*_=self.f.proposal(slip='.1')
  with self.assertRaisesRegex(m.Blocked,'slippage'):self.f.approve(t)
  t,*_=self.f.proposal(out=2_300_000)
  with self.assertRaisesRegex(m.Blocked,'slippage'):self.f.approve(t)
 def test_three_positions_cap(self):
  for mint in [MINT,M2,M3]:
   t,*_=self.f.proposal(usd='1',mint=mint);self.f.fill(t)
  t,*_=self.f.proposal(usd='1',mint=M4)
  with self.assertRaisesRegex(m.Blocked,'Max 3'):self.f.approve(t)
 def test_per_mint_pyramiding_cap(self):
  t,*_=self.f.proposal();self.f.fill(t);t,*_=self.f.proposal(usd='.1')
  with self.assertRaisesRegex(m.Blocked,'Per-mint'):self.f.approve(t)
 def test_sell_without_holdings(self):
  t,*_=self.f.proposal('SELL',quantity='1')
  with self.assertRaises(m.Blocked):self.f.approve(t)
 def test_insufficient_cash_reconciled(self):
  # Isolated replay state injection tests validation, not an impossible capital reset.
  t,row,a,q,_=self.f.proposal();_,s=self.f.ledger.snapshot();s['cash']=D('.01');s['equity']=[{'day':self.f.now.astimezone(m.TZ).date().isoformat(),'baseline':'.01','fresh':True,'net_equity':'.01'}]
  with self.assertRaisesRegex(m.Blocked,'cash'):self.f.broker._checks(t,row,a,q,s,self.f.now)
 def test_stale_open_position_marks_block_entries(self):
  t,*_=self.f.proposal();self.f.fill(t);self.f.now+=timedelta(seconds=61)
  self.assertFalse(self.f.ledger.portfolio()['fresh'])
  t,*_=self.f.proposal(usd='1',mint=M2)
  with self.assertRaisesRegex(m.Blocked,'marks'):self.f.approve(t)
 def test_daily_loss_and_restart_latch_no_reset(self):
  for mint in [MINT,M2]:
   t,*_=self.f.proposal(mint=mint);self.f.fill(t)
  self.f.ledger.mark([self.f.row('.4',mint) for mint in (MINT,M2)])
  v=self.f.ledger.portfolio();self.assertTrue(v['daily_halted']);self.assertLessEqual(D(v['daily_pnl']),D('-2.5'))
  self.f.ledger=m.PaperLedger(self.f.ledger.path,lambda:self.f.now);self.f.broker=m.PaperBroker(self.f.ledger,self.f.gates)
  self.f.ledger.mark([self.f.row('1',mint) for mint in (MINT,M2)])
  t,*_=self.f.proposal(usd='1',mint=M3)
  with self.assertRaisesRegex(m.Blocked,'halt latched'):self.f.approve(t)
 def test_daily_halt_exits_still_require_global_gates(self):
  t,*_=self.f.proposal();self.f.fill(t)
  with self.f.ledger.db() as c:self.f.ledger._append(c,'TEST_HALT','halt',{'day':self.f.now.astimezone(m.TZ).date().isoformat()})
  t,*_=self.f.proposal('SELL',quantity='1');self.f.fill(t)
 def test_timezone_and_drawdown(self):
  self.f.now=datetime(2026,11,8,18,30,tzinfo=timezone.utc)
  self.assertEqual(self.f.ledger.portfolio()['day'],'2026-11-09')
  t,*_=self.f.proposal();self.f.fill(t);self.f.ledger.mark([self.f.row('.8')])
  v=self.f.ledger.portfolio();self.assertGreater(D(v['drawdown_usd']),0);self.assertGreater(D(v['drawdown_pct']),0)
 def test_unknown_marks_no_zero_equity(self):
  t,*_=self.f.proposal();self.f.fill(t);_,s=self.f.ledger.snapshot();s['marks']={}
  v=self.f.ledger._valuation(s,self.f.now);self.assertIsNone(v['net_equity']);self.assertFalse(v['fresh'])
 def test_marks_wrong_pair_stale_and_time_reversal(self):
  t,*_=self.f.proposal();self.f.fill(t)
  for change in [{'pair':M2},{'fetched_utc':m.stamp(self.f.now-timedelta(seconds=70))},{'price_usd':'NaN'}]:
   with self.assertRaises(m.Blocked):self.f.ledger.mark([dict(self.f.row(),**change)])
 def test_ledger_append_only_triggers(self):
  with self.f.ledger.db() as c:
   for query in ['DELETE FROM paper_events_v1','UPDATE paper_events_v1 SET hash="bad"']:
    with self.assertRaises(sqlite3.IntegrityError):c.execute(query)
 def test_hash_tamper_fails_startup(self):
  with self.f.ledger.db() as c:
   c.execute('DROP TRIGGER paper_events_no_update');c.execute('UPDATE paper_events_v1 SET payload=? WHERE seq=1',('{"usd":"500"}',))
  with self.assertRaises(m.Blocked):m.PaperLedger(self.f.ledger.path)
 def test_exports_and_source_provenance(self):
  t,*_=self.f.proposal();self.f.fill(t)
  rows=self.f.ledger.export('fill');self.assertIn(m.JUP,rows);self.assertIn('utc',rows)
  self.assertIn('prev_hash',self.f.ledger.export(fmt='csv'));self.assertEqual(len(rows.splitlines()),1)
 def test_reconcile_no_resend(self):
  t,*_=self.f.proposal();self.assertIn('NO COMMITTED',self.f.broker.reconcile(t['decision_id'])['status'])
  self.f.fill(t);self.assertEqual(self.f.broker.reconcile(t['decision_id'])['status'],'FILLED / PAPER')
 def test_legacy_observations_not_fills(self):
  path=self.f.root/'legacy.sqlite';research=m.ResearchStore(path);research.save_rows([dict(self.f.row(),symbol='TEST_ONLY')]);research.ticket({'mint':MINT,'usd':'2.5'})
  ledger=m.PaperLedger(path);self.assertEqual(D(ledger.portfolio()['cash']),50);self.assertEqual(len(ledger.snapshot()[1]['fills']),0)
  self.assertEqual(len(research.rows()),1)

 def test_postcommit_timeout_unknown_result_reconcile_not_resend(self):
  from contextlib import contextmanager
  t,*_=self.f.proposal();app=self.f.approve(t);original=self.f.ledger.db
  @contextmanager
  def ambiguous():
   with original() as c:yield c
   raise OSError('TEST_ONLY: response lost after durable commit')
  self.f.ledger.db=ambiguous
  with self.assertRaises(m.UnknownResult):self.f.broker.place(t['decision_id'],app['approval_id'],m.digest(t))
  self.f.ledger.db=original
  self.assertEqual(self.f.broker.reconcile(t['decision_id'])['status'],'FILLED / PAPER')
  self.assertEqual(len(self.f.ledger.snapshot()[1]['fills']),1)
 def test_precommit_storage_error_rolls_back_atomic_batch(self):
  t,*_=self.f.proposal();app=self.f.approve(t);original=self.f.ledger._append
  def fail(c,eid,kind,payload):
   if kind=='fill':raise sqlite3.OperationalError('TEST_ONLY disk failure')
   return original(c,eid,kind,payload)
  self.f.ledger._append=fail
  with self.assertRaises(m.UnknownResult):self.f.broker.place(t['decision_id'],app['approval_id'],m.digest(t))
  self.f.ledger._append=original
  events,state=self.f.ledger.snapshot();self.assertEqual(len(state['fills']),0)
  self.assertFalse(any(e['kind']=='order' for e in events));self.assertEqual(state['cash'],50)
 def test_persistent_daily_baseline_dhaka_new_day(self):
  t,*_=self.f.proposal();self.f.fill(t);self.f.ledger.mark([self.f.row('1.5')])
  prior=self.f.ledger.portfolio()['net_equity'];self.f.now+=timedelta(days=1)
  self.f.ledger.mark([self.f.row('1')]);v=self.f.ledger.portfolio()
  self.assertEqual(D(v['baseline']),D(prior));self.assertLess(D(v['daily_pnl']),0)
 def test_sell_at_future_quote_not_reused_buy_quote(self):
  t,row,a,q,_=self.f.proposal();self.f.fill(t)
  sell=dict(t,side='SELL',usd='0',quantity='1',decision_id='TEST_ONLY_SELL_MISMATCH')
  self.f.broker.propose(sell,row,a,q)
  with self.assertRaises(m.Blocked):self.f.approve(sell)
 def test_wrong_audit_mint_and_tamper_block_actual_approval(self):
  t,row,a,q,_=self.f.proposal();_,state=self.f.ledger.snapshot()
  for change in [{'mint':M2},{'mint_authority':PAIR},{'subset_verdict':'BLIND'}]:
   with self.assertRaises(m.Blocked):self.f.broker._checks(t,row,dict(a,**change),q,state,self.f.now)
 def test_forbidden_audit_blocks_before_fill_even_with_signed_risk(self):
  for field in ['mintAuthority','freezeAuthority']:
   t,row,a,q,_=self.f.proposal();raw=self.f.raw_authority();raw['result']['value']['data']['parsed']['info'][field]=PAIR
   bad=self.f.audit(raw=raw);t['decision_id']+='_'+field;t['audit_id']=bad['audit_id']
   self.f.risks[MINT]['audit_id']=bad['audit_id'];self.f.sign();self.f.broker.propose(t,row,bad,q)
   with self.assertRaises(m.Blocked):self.f.approve(t)

 def test_unauthenticated_and_wrong_owner_cannot_approve(self):
  t,*_=self.f.proposal()
  for identity in [None,lambda:'b'*64]:
   b=m.PaperBroker(self.f.ledger,self.f.gates,human_identity=identity)
   with self.assertRaisesRegex(m.Blocked,'owner session'):b.approve(t['decision_id'],m.digest(t),'CONFIRM PAPER '+t['decision_id'])
 def test_approved_ticket_cannot_be_placed_by_other_visitor(self):
  t,*_=self.f.proposal();app=self.f.approve(t)
  b=m.PaperBroker(self.f.ledger,self.f.gates,human_identity=lambda:'b'*64)
  with self.assertRaises(m.Blocked):b.place(t['decision_id'],app['approval_id'],m.digest(t))

class EvidenceTests(unittest.TestCase):
 def setUp(self):self.f=Fixture()
 def tearDown(self):self.f.cleanup()
 def test_authorities_active_both_forbidden(self):
  for key in ['mintAuthority','freezeAuthority']:
   raw=self.f.raw_authority();raw['result']['value']['data']['parsed']['info'][key]=PAIR
   self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'FORBIDDEN')
 def test_missing_authority_no_false_null_pass(self):
  for key in ['mintAuthority','freezeAuthority','isInitialized','decimals','supply']:
   raw=self.f.raw_authority();raw['result']['value']['data']['parsed']['info'].pop(key)
   self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'BLIND')
 def test_invalid_rpc_shapes(self):
  for raw in [{},{'error':{}},{'result':{'value':None,'context':{'slot':1}}},[]]:
   self.assertEqual(m.parse_authority(raw,MINT,self.f.meta(m.RPC))['subset_verdict'],'BLIND')
 def test_invalid_program_slot_and_parser(self):
  raw=self.f.raw_authority();raw['result']['value']['owner']=PAIR;self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'BLIND')
  raw=self.f.raw_authority();raw['result']['context']['slot']=None;self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'BLIND')
  raw=self.f.raw_authority();raw['result']['value']['data']=['base64','base64'];self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'BLIND')
 def test_token2022_fee_tax_and_mutable_zero_tax(self):
  ext={'extension':'transferFeeConfig','state':{'transferFeeConfigAuthority':None,
   'olderTransferFee':{'transferFeeBasisPoints':20},'newerTransferFee':{'transferFeeBasisPoints':20}}}
  a=self.f.audit(raw=self.f.raw_authority(m.TOKEN2022,[ext]));self.assertEqual(a['subset_verdict'],'FORBIDDEN')
  ext['state']['olderTransferFee']['transferFeeBasisPoints']=0;ext['state']['newerTransferFee']['transferFeeBasisPoints']=0
  a=self.f.audit(raw=self.f.raw_authority(m.TOKEN2022,[ext]));self.assertEqual(a['subset_verdict'],'PASS SUBSET')
  ext['state']['transferFeeConfigAuthority']=PAIR
  self.assertEqual(self.f.audit(raw=self.f.raw_authority(m.TOKEN2022,[ext]))['subset_verdict'],'BLIND')
 def test_token2022_missing_inventory_unknown_hook_and_fee_schema(self):
  raw=self.f.raw_authority(m.TOKEN2022);raw['result']['value']['data']['space']=400
  self.assertEqual(self.f.audit(raw=raw)['subset_verdict'],'BLIND')
  for ext in [{'extension':'transferHook'},{'extension':'transferFeeConfig','state':{}},{'extension':'futureUnknown'}]:
   self.assertEqual(self.f.audit(raw=self.f.raw_authority(m.TOKEN2022,[ext]))['subset_verdict'],'BLIND')
 def test_malformed_quote_missing_fields_route_price_amount_identity(self):
  t,row,a,q,raw=self.f.proposal()
  for key,val in [('routePlan',[]),('outAmount','NaN'),('priceImpact',None),('inAmount','wrong'),('outputMint',M2),('feeBps',None),('transaction','unexpected'),('taker',PAIR)]:
   altered=copy.deepcopy(raw);altered[key]=val
   with self.assertRaises(m.Blocked):m.RouteModel.parse(altered,self.f.meta(m.JUP+'?TEST_ONLY=1'),t,a,2500000,m.USDC,MINT)
 def test_market_identity_missing_stale_cached_future_and_liquidity(self):
  t,row,a,q,_=self.f.proposal()
  for mutate in [{'mint':M2},{'pair':M2},{'price_usd':None},{'liquidity_usd':None},{'liquidity_usd':'100'},
   {'fetched_utc':m.stamp(self.f.now-timedelta(seconds=61))},{'http_age':'120'},
   {'http_date':format_datetime(self.f.now-timedelta(seconds=120),usegmt=True)},
   {'http_date':None},{'fetched_utc':m.stamp(self.f.now+timedelta(seconds=1))}]:
   with self.assertRaises(m.Blocked):m.RouteModel.simulate(t,dict(row,**mutate),a,q,self.f.now)
 def test_quote_hash_or_timestamp_corrupt(self):
  t,row,a,q,_=self.f.proposal()
  for mutate in [{'output_atomic':'9999999'},{'expires_utc':m.stamp(self.f.now)},{'http_age':'90'}]:
   with self.assertRaises(m.Blocked):m.RouteModel.simulate(t,row,a,dict(q,**mutate),self.f.now)
 def test_entry_missing_volume(self):
  t,row,a,q,_=self.f.proposal();row['volume_h1_usd']=None;_,s=self.f.ledger.snapshot()
  with self.assertRaises(m.Blocked):self.f.broker._checks(t,row,a,q,s,self.f.now)
 def test_provider_error_no_synthetic_fallback(self):
  store=m.ResearchStore(self.f.root/'scanner.sqlite')
  def broken(path):raise m.ProviderError('HTTP 429 rate limit')
  result=m.scan(store,broken);self.assertEqual(result['new'],0);self.assertEqual(store.rows(),[])
 def test_denied_source_latches_no_retry(self):
  store=m.ResearchStore(self.f.root/'scanner.sqlite');calls=[]
  def denied(path):calls.append(path);raise m.ProviderError('HTTP 403 forbidden')
  m.scan(store,denied);m.scan(store,denied);self.assertEqual(len(calls),1);self.assertTrue(store.get('provider_blocked'))
 def test_scan_schema_and_exact_mint_identity(self):
  with self.assertRaises(m.ProviderError):m.parse_profiles({})
  with self.assertRaises(m.ProviderError):m.parse_pairs({},[MINT],{})
  raw=[{'chainId':'solana','baseToken':{'address':M2},'quoteToken':{},'pairAddress':PAIR,'priceUsd':'1'}]
  self.assertEqual(m.parse_pairs(raw,[MINT],self.f.meta(m.API)),[])
 def test_boolean_nan_numbers_not_accepted(self):
  for x in [True,float('nan'),float('inf'),None]:
   with self.assertRaises(m.Blocked):m.dec(x)
 def test_forbidden_rpc_and_quote_endpoint_static(self):
  import ast
  source=Path(m.__file__).read_text();tree=ast.parse(source)
  for node in ast.walk(tree):
   if isinstance(node,ast.Constant) and isinstance(node.value,str):
    for forbidden in ['sendTransaction','sendRawTransaction','/swap/v2/execute','/swap/v2/build','/swap/v2/submit','private_key','seed_phrase']:
     self.assertNotIn(forbidden,node.value)
  self.assertNotIn('eval(',source);self.assertNotIn('exec(',source)

 def test_scan_success_cooldown_and_retains_original_snapshot_time(self):
  store=m.ResearchStore(self.f.root/'scanner.sqlite');calls=[]
  raw=[{'chainId':'solana','baseToken':{'address':MINT,'symbol':'TEST_ONLY'},'quoteToken':{'address':m.USDC},
    'pairAddress':PAIR,'priceUsd':'1','liquidity':{'usd':10000},'volume':{'h1':1000}}]
  def fetch(path):
   calls.append(path)
   return ([{'chainId':'solana','tokenAddress':MINT}] if path.startswith('/token-profiles') else raw),self.f.meta(m.API+path)
  r=m.scan(store,fetch);self.assertEqual(r['new'],1);self.assertEqual(len(store.rows()),1)
  m.scan(store,fetch);self.assertEqual(len(calls),2)
  original=store.rows()[0]['fetched_utc'];store.set('last_attempt','2000-01-01T00:00:00+00:00')
  def failed(path):raise m.ProviderError('HTTP 429')
  m.scan(store,failed);self.assertEqual(store.rows()[0]['fetched_utc'],original)
 def test_quote_provider_expiry_slippage_and_route_graph(self):
  t,row,a,q,raw=self.f.proposal()
  for change in [{'expireAt':'bad'},{'routePlan':[{'percent':100,'bps':10000,'swapInfo':{'ammKey':PAIR,'inputMint':M3,'outputMint':MINT,'inAmount':'1','outAmount':'1'}}]}]:
   with self.assertRaises(m.Blocked):m.RouteModel.parse(dict(raw,**change),self.f.meta(m.JUP+'?TEST_ONLY=1'),t,a,2500000,m.USDC,MINT)
  earlier=m.stamp(self.f.now+timedelta(seconds=5))
  q=m.RouteModel.parse(dict(raw,expireAt=earlier),self.f.meta(m.JUP+'?TEST_ONLY=1'),t,a,2500000,m.USDC,MINT)
  self.assertEqual(q['expires_utc'],earlier)
  with self.assertRaises(m.Blocked):m.RouteModel.simulate(dict(t,slippage_pct='2'),row,a,q,self.f.now)
 def test_nonfinite_negative_fee_and_stablecoin_depeg(self):
  t,row,a,q,raw=self.f.proposal()
  with self.assertRaises(m.Blocked):m.RouteModel.parse(dict(raw,feeBps=-1),self.f.meta(m.JUP+'?TEST_ONLY=1'),t,a,2500000,m.USDC,MINT)
  q['in_usd']='2';q['quote_id']=m.digest({k:v for k,v in q.items() if k!='quote_id'})
  t['quote_id']=q['quote_id']
  with self.assertRaisesRegex(m.Blocked,'USDC/USD'):m.RouteModel.simulate(t,row,a,q,self.f.now)
 def test_transfer_fee_negative_and_noninteger_blind(self):
  for bps in [-1,'1.5',10001]:
   ext={'extension':'transferFeeConfig','state':{'transferFeeConfigAuthority':None,
    'olderTransferFee':{'transferFeeBasisPoints':bps},'newerTransferFee':{'transferFeeBasisPoints':bps}}}
   self.assertEqual(self.f.audit(raw=self.f.raw_authority(m.TOKEN2022,[ext]))['subset_verdict'],'BLIND')

 def test_nonzero_network_fee_not_silently_ignored(self):
  t,row,a,q,raw=self.f.proposal()
  for field in ['signatureFeeLamports','prioritizationFeeLamports','rentFeeLamports']:
   with self.assertRaisesRegex(m.Blocked,'SOL/USD'):
    m.RouteModel.parse(dict(raw,**{field:500000}),self.f.meta(m.JUP+'?TEST_ONLY=1'),t,a,2500000,m.USDC,MINT)

if __name__=='__main__':unittest.main(verbosity=2)
