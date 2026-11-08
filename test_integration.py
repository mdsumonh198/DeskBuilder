"""Keyless adapter tests using captured supported CLI reads; no engine mutation."""
import unittest,json,tempfile,subprocess,copy,os,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from email.utils import format_datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import trading_terminal as m
FIXTURES=Path(__file__).parent/'fixtures'/'cli'
MINT='So11111111111111111111111111111111111111112'
PAIR='11111111111111111111111111111111'
class AdapterTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='KEYLESS_STATUS_TEST_ONLY_');self.root=Path(self.temp.name)
  self.cli=self.root/'TEST_ONLY_CLI';self.cli.write_text('# TEST ONLY; never executed\n');self.cli.chmod(0o755)
  self.outputs={key:json.loads((FIXTURES/(key+'.json')).read_text()) for key in m.READ_COMMANDS}
  self.now=datetime(2026,11,8,19,38,20,tzinfo=timezone.utc);self.calls=[]
 def tearDown(self):self.temp.cleanup()
 def runner(self,args,**kwargs):
  self.calls.append((args,kwargs));key=next(k for k,v in m.READ_COMMANDS.items() if tuple(args[1:])==v)
  r=self.outputs[key]
  return subprocess.CompletedProcess(args,r['exit_code'],r['stdout'],r['stderr'])
 def adapter(self,runner=None):return m.LocalDeskStatus(str(self.cli),str(self.root),runner or self.runner,lambda:self.now)
 def edit_status(self,key,**fields):
  p=json.loads(self.outputs[key]['stdout']);p.update(fields);self.outputs[key]['stdout']=json.dumps(p)
 def test_genuine_recorded_reads_connect_readonly_halted(self):
  s=self.adapter().snapshot();self.assertEqual(s['connection'],'CONNECTED READ-ONLY');self.assertEqual(s['desk_state'],'HALTED')
  self.assertEqual(s['effective_mode'],'paper');self.assertEqual(s['engine_portfolio']['equity_sol'],'10.000000000')
  self.assertEqual(s['engine_portfolio']['autonomy'],'autonomous-paper');self.assertEqual(s['ticket_count'],0)
  self.assertFalse(s['capabilities']['can_place_orders']);self.assertFalse(s['capabilities']['exact_approval_read'])
  self.assertTrue(s['policy_status'].startswith('MISMATCH'));self.assertEqual(len(self.calls),5)
 def test_only_exact_allowlisted_read_commands_no_shell(self):
  self.adapter().snapshot()
  for args,kwargs in self.calls:
   self.assertIn(tuple(args[1:]),m.READ_COMMANDS.values());self.assertNotIn('shell',kwargs);self.assertEqual(kwargs['timeout'],12)
  self.assertNotIn(('run',),m.READ_COMMANDS.values())
 def test_app_settings_do_not_break_engine_unknown_env_validator(self):
  with patch.dict(os.environ,{'PUMPGROK_CLI':str(self.cli),'PUMPGROK_DESK_DIR':str(self.root),'PUMPGROK_TERMINAL_DB':'TEST_ONLY','PUMPGROK_MODE':'paper'},clear=False):
   self.adapter().snapshot()
  for args,kwargs in self.calls:
   for key in ['PUMPGROK_CLI','PUMPGROK_DESK_DIR','PUMPGROK_TERMINAL_DB']:self.assertNotIn(key,kwargs['env'])
   self.assertEqual(kwargs['env']['PUMPGROK_MODE'],'paper')
 def test_unknown_cloud_is_disconnected_no_fallback(self):
  a=m.LocalDeskStatus(str(self.root/'not-installed'),str(self.root),self.runner,lambda:self.now)
  s=a.snapshot();self.assertEqual(s['connection'],'DISCONNECTED');self.assertIn('Community Cloud',s['errors'][0]);self.assertFalse(self.calls)
 def test_unsafe_permissions_no_command_execution(self):
  self.cli.chmod(0o777);s=self.adapter().snapshot();self.assertEqual(s['connection'],'DISCONNECTED');self.assertFalse(self.calls)
 def test_stale_source_not_refreshed_by_new_receipt_time(self):
  self.now+=timedelta(seconds=90);s=self.adapter().snapshot();self.assertEqual(s['connection'],'DISCONNECTED')
  self.assertFalse(s['capabilities']['state_read']);self.assertIn('stale',' '.join(s['errors']).lower())
 def test_unknown_boolean_missing_meta_and_malformed_json(self):
  for bad in ['{}','[]','not json',json.dumps({'meta':{}})]:
   self.outputs['state']['stdout']=bad;s=self.adapter().snapshot();self.assertEqual(s['connection'],'DISCONNECTED')
  self.outputs['state']=json.loads((FIXTURES/'state.json').read_text());self.edit_status('state',halted='false')
  self.assertEqual(self.adapter().snapshot()['connection'],'DISCONNECTED')
 def test_conflicting_sources_not_clear(self):
  self.edit_status('kill',halted=False,kill_switch_active=False,reasons=[])
  s=self.adapter().snapshot();self.assertEqual(s['connection'],'DISCONNECTED');self.assertIn('Conflicting',' '.join(s['errors']))
 def test_live_mode_detected_without_forcing_paper(self):
  self.edit_status('state',effective_mode='live');s=self.adapter().snapshot()
  self.assertEqual(s['desk_state'],'UNSAFE MODE — STOP')
  self.assertTrue(all('--mode' not in args for args,_ in self.calls))
 def test_doctor_exit_zero_is_not_complete_health(self):
  s=self.adapter().snapshot();self.assertEqual(s['doctor']['gateway'],'NOT IMPLEMENTED')
  self.assertIn('ONLY',s['doctor']['scope']);self.assertNotIn('healthy',s['doctor'])
 def test_timeout_failure_and_empty_report(self):
  def timed(args,**kw):
   if args[1:] == ['state','status','--seat','chief']:raise subprocess.TimeoutExpired(args,12)
   return self.runner(args,**kw)
  s=self.adapter(timed).snapshot();self.assertEqual(s['connection'],'DISCONNECTED');self.assertIn('timed out',' '.join(s['errors']))
  self.outputs['state']['exit_code']=1;self.assertEqual(self.adapter().snapshot()['connection'],'DISCONNECTED')
  self.outputs['portfolio']['stdout']='';s=self.adapter().snapshot();self.assertFalse(s['capabilities']['portfolio_report_read'])
 def test_fake_capability_claims_never_clear_risk_or_approvals(self):
  self.edit_status('state',capabilities={'can_place_orders':True,'full_risk_clear':True},approval_id='fake')
  s=self.adapter().snapshot();self.assertFalse(s['capabilities']['can_place_orders']);self.assertFalse(s['capabilities']['ticket_scoped_full_risk_read'])
  with self.assertRaisesRegex(m.Blocked,'GLOBAL KILL'):m.DeskEvidence(self.adapter()).read(self.now)
 def test_clear_halt_is_not_full_trade_clearance(self):
  for key in ['state','kill']:self.edit_status(key,halted=False,kill_switch_active=False,reasons=[])
  s=self.adapter().snapshot();self.assertEqual(s['connection'],'CONNECTED READ-ONLY')
  with self.assertRaisesRegex(m.Blocked,'unavailable'):m.DeskEvidence(self.adapter()).read(self.now)
 def test_no_roster_liveness_inference_and_separate_units(self):
  s=self.adapter().snapshot();self.assertTrue(all(v=='NOT CONNECTED' for v in s['agents'].values()))
  self.assertEqual(s['engine_portfolio']['units'],'SOL');self.assertNotIn('cash_usd',s['engine_portfolio'])
 def test_no_private_key_signature_configuration_in_runtime(self):
  text=Path(m.__file__).read_text()
  for forbidden in ['Ed25519','PUMPGROK_GATE_PUBLIC_KEY','PUMPGROK_GATE_ATTESTATION','binding.key','cryptography','base64.b64decode']:
   self.assertNotIn(forbidden,text)

class MonitorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='MONITOR_TEST_ONLY_');self.root=Path(self.temp.name);self.store=m.ResearchStore(self.root/'TEST_ONLY.sqlite');self.session={};self.calls=[]
 def tearDown(self):self.temp.cleanup()
 def fetch(self,path):
  self.calls.append(path);now=datetime.now(timezone.utc)
  data=[{'chainId':'solana','tokenAddress':MINT}] if path.startswith('/token-profiles') else [
   {'chainId':'solana','baseToken':{'address':MINT,'symbol':'TEST_ONLY'},'quoteToken':{'address':m.USDC},'pairAddress':PAIR,'priceUsd':'1','liquidity':{'usd':100000},'volume':{'h1':1000}}]
  return data,{'url':m.API+path,'fetched_utc':m.stamp(now),'http_date':format_datetime(now,usegmt=True),'http_age':'0','provider_observation_utc':None}
 def test_stopped_performs_no_read(self):
  r=m.monitor_tick(self.store,self.session,self.fetch);self.assertEqual(r['state'],'STOPPED');self.assertFalse(self.calls)
 def test_start_actual_reads_counter_and_rerun_cooldown(self):
  m.start_market_monitor(self.session);r=m.monitor_tick(self.store,self.session,self.fetch)
  self.assertEqual(len(self.calls),2);self.assertEqual(r['successful_cycles'],1);self.assertEqual(r['pair_count'],1)
  m.monitor_tick(self.store,self.session,self.fetch);self.assertEqual(len(self.calls),2);self.assertEqual(self.session['monitor_successful_cycles'],1)
  self.assertEqual(self.store.cash(),50);self.assertFalse(self.store.tickets())
 def test_stop_blocks_next_tick_and_restart_does_not_reset_counts(self):
  m.start_market_monitor(self.session);m.monitor_tick(self.store,self.session,self.fetch);m.stop_market_monitor(self.session)
  m.monitor_tick(self.store,self.session,self.fetch);self.assertEqual(len(self.calls),2)
  m.start_market_monitor(self.session);m.monitor_tick(self.store,self.session,self.fetch);self.assertEqual(self.session['monitor_successful_cycles'],1)
 def test_unsafe_mode_stops_without_any_source_read(self):
  m.start_market_monitor(self.session);r=m.monitor_tick(self.store,self.session,self.fetch,{'desk_state':'UNSAFE MODE — STOP'})
  self.assertEqual(r['state'],'STOPPED');self.assertFalse(self.calls)
 def test_failed_provider_is_real_failure_not_success_or_profit(self):
  m.start_market_monitor(self.session)
  def fail(path):raise m.ProviderError('HTTP 429')
  r=m.monitor_tick(self.store,self.session,fail);self.assertEqual(r['attempted_cycles'],1);self.assertEqual(r['successful_cycles'],0)
  self.assertFalse(self.store.rows());self.assertEqual(self.store.cash(),50)

if __name__=='__main__':unittest.main(verbosity=2)
