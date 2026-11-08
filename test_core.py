import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone,timedelta
from market_paper_terminal.core import *
M='So11111111111111111111111111111111111111112'
P='11111111111111111111111111111111'
META={'url':API+'/tokens/v1/solana/'+M,'fetched_utc':utc(),'http_age':None,'http_date':None,'provider_observation_utc':None}
PAIR={'chainId':'solana','pairAddress':P,'dexId':'fixture-venue','baseToken':{'address':M,'symbol':'FIXTURE'},'priceUsd':'1.25','liquidity':{'usd':1000},'volume':{'h1':12}}
def fixture(path):
 return ([{'chainId':'solana','tokenAddress':M}] if 'profiles' in path else [PAIR]),META.copy()
class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'research.db')
 def tearDown(self):self.tmp.cleanup()
 def test_parse(self):
  self.assertEqual(parse_profiles([{'chainId':'solana','tokenAddress':'fake'}]),[])
  with self.assertRaises(ProviderError):parse_profiles({})
  with self.assertRaises(ProviderError):parse_pairs({},[M],META)
  self.assertEqual(parse_pairs([PAIR],['wrongmint'],META),[])
  row=parse_pairs([PAIR],[M],META)[0];self.assertEqual(row['price_usd'],1.25)
  self.assertIsNone(number('NaN'));self.assertIsNone(number('-1'));self.assertIsNone(number(True))
  self.assertEqual(audit(row)['Mint authority'],'BLIND — RPC audit not connected')
 def test_persistence_cooldown_idempotency(self):
  r=scan(self.store,fixture);self.assertEqual(r['new'],1)
  again=scan(self.store,lambda _:self.fail('cooldown must not fetch'));self.assertTrue(again['cached'])
  self.store.set('last_attempt',(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat())
  self.assertEqual(scan(self.store,fixture)['new'],0)
  fresh=Store(self.store.path);self.assertEqual(len(fresh.rows()),1);self.assertEqual(fresh.cash(),50)
  ticket={'mint':M,'side':'BUY','usd':'2.50','slippage':'3'}
  self.assertEqual(fresh.ticket(ticket),fresh.ticket(ticket));self.assertEqual(len(fresh.tickets()),1)
  self.assertEqual(Store(self.store.path).cash(),50)
 def test_failure_retains_lastgood_and_no_fallback(self):
  scan(self.store,fixture)
  self.store.set('last_attempt',None)
  def fail(_):raise ProviderError('HTTP 403: forbidden')
  self.assertEqual(scan(self.store,fail)['new'],0)
  self.assertEqual(self.store.get('health')['status'],'BLOCKED')
  self.assertEqual(len(self.store.rows()),1)
  scan(self.store,lambda _:self.fail('denied provider must not be retried'))
  other=Store(Path(self.tmp.name)/'other.db')
  scan(other,lambda _: (_ for _ in ()).throw(ProviderError('Invalid JSON')))
  self.assertEqual(other.rows(),[]);self.assertEqual(other.cash(),50)
 def test_no_bypass_and_limits(self):
  row=parse_pairs([PAIR],[M],META)[0]
  ticket={'mint':M,'usd':'2.50','slippage':'3'}
  reasons=gate(ticket,row,halt='CLEARED (fixture)',config_agrees=True,audit_clear=True,exact_approval=True)
  self.assertIn('NOT CONNECTED',reasons[0]);self.assertTrue(any('quote' in r for r in reasons))
  reasons=gate({**ticket,'usd':'2.51','slippage':'3.01'},row,open_positions=3,daily_pnl=Decimal('-2.50'))
  for token in ['Size must','Slippage must','Max 3','entries frozen']:self.assertTrue(any(token in r for r in reasons))
  stale={**row,'fetched_utc':(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()}
  self.assertTrue(any('stale' in r for r in gate(ticket,stale)))
  path=Path(self.tmp.name)/'KILLSWITCH';path.write_text('ACTIVE')
  self.assertTrue(halt_status(path).startswith('ACTIVE'));self.assertEqual(path.read_text(),'ACTIVE')
  self.assertTrue(halt_status(Path(self.tmp.name)/'absent').startswith('UNKNOWN'))
if __name__=='__main__':unittest.main()
