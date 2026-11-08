"""TEST ONLY: isolated deployment starts with just the two distribution files."""
import os
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]

class DeploymentTests(unittest.TestCase):
 def test_two_file_no_helper_package_english_dark_and_no_profit(self):
  with tempfile.TemporaryDirectory(prefix='PAPER_APPTEST_ONLY_') as temp:
   root=Path(temp)
   for name in ['trading_terminal.py','requirements.txt']:shutil.copy2(ROOT/name,root/name)
   self.assertEqual(len(list(root.iterdir())),2)
   with patch.dict(os.environ,{'PUMPGROK_TERMINAL_DB':str(root/'TEST_ONLY.sqlite'),'PUMPGROK_CLI':str(root/'not-installed'),'PUMPGROK_DESK_DIR':str(root)},clear=False):
    at=AppTest.from_file(str(root/'trading_terminal.py'),default_timeout=30).run()
    self.assertEqual(len(at.exception),0,str(at.exception))
    labels=[x.label for x in at.metric];self.assertIn('Paper Cash',labels)
    self.assertEqual(next(x.value for x in at.metric if x.label=='Paper Cash'),'$50.00')
    self.assertEqual(next(x.value for x in at.metric if x.label=='Realized P&L'),'$0.00')
    text='\n'.join(str(x.value) for x in at.markdown)
    self.assertIn('Desk Status Adapter v4',text);self.assertIn('NOT CONNECTED',text);self.assertIn('#070b14',text)
    import re
    self.assertFalse(re.search('[\u0980-\u09ff]',text))
    self.assertEqual([x.label for x in at.tabs],['Overview','Scanner','Positions','Paper Tickets / Approvals','Ledger / Activity','Safety / Config'])
    at.run();self.assertEqual(len(at.exception),0)
    self.assertEqual(next(x.value for x in at.metric if x.label=='Net Equity (indicative MTM)'),'$50.00')

 def test_proposal_view_blocks_ui_under_actual_global_halt_or_unknown_gate(self):
  from test_paper_system import Fixture
  f=Fixture()
  try:
   f.proposal()
   with tempfile.TemporaryDirectory(prefix='PAPER_APPTEST_TWO_FILES_') as temp:
    root=Path(temp)
    for name in ['trading_terminal.py','requirements.txt']:shutil.copy2(ROOT/name,root/name)
    with patch.dict(os.environ,{'PUMPGROK_TERMINAL_DB':f.ledger.path,'PUMPGROK_CLI':str(root/'not-installed'),'PUMPGROK_DESK_DIR':str(root)},clear=False):
     at=AppTest.from_file(str(root/'trading_terminal.py'),default_timeout=30).run()
     self.assertEqual(len(at.exception),0,str(at.exception))
     approve=next(b for b in at.button if b.label=='Approve Exact Paper Ticket')
     place=next(b for b in at.button if b.label=='Place Approved Simulated Order ONCE')
     self.assertTrue(approve.disabled);self.assertTrue(place.disabled)
     self.assertTrue(any('NO FILL:' in str(x.value) for x in at.error))
     self.assertEqual(len(f.ledger.snapshot()[1]['fills']),0)
  finally:f.cleanup()

 def test_start_stop_native_controls_update_only_actual_fixture_reads(self):
  import json
  from datetime import datetime,timezone
  from email.utils import format_datetime
  calls=[]
  mint='So11111111111111111111111111111111111111112';pair='11111111111111111111111111111111'
  class Response:
   def __init__(self,url):
    self.headers={'Content-Type':'application/json','Date':format_datetime(datetime.now(timezone.utc),usegmt=True),'Age':'0'}
    self.data=([{'chainId':'solana','tokenAddress':mint}] if '/token-profiles/' in url else [
     {'chainId':'solana','baseToken':{'address':mint,'symbol':'TEST_ONLY'},'quoteToken':{'address':mint},'pairAddress':pair,'priceUsd':'1','liquidity':{'usd':100000},'volume':{'h1':1000}}])
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,n):return json.dumps(self.data).encode()
  class Opener:
   def open(self,request,**kwargs):calls.append(request.full_url);return Response(request.full_url)
  with tempfile.TemporaryDirectory(prefix='MONITOR_UI_TWO_FILES_TEST_ONLY_') as d:
   root=Path(d)
   for name in ['trading_terminal.py','requirements.txt']:shutil.copy2(ROOT/name,root/name)
   with patch.dict(os.environ,{'PUMPGROK_TERMINAL_DB':str(root/'TEST_ONLY.sqlite'),'PUMPGROK_CLI':str(root/'not-installed'),'PUMPGROK_DESK_DIR':str(root)},clear=False),patch('urllib.request.build_opener',return_value=Opener()):
    at=AppTest.from_file(str(root/'trading_terminal.py'),default_timeout=30).run()
    self.assertFalse(calls);self.assertFalse(at.exception)
    next(b for b in at.button if b.label=='Start Market Monitor').click().run()
    self.assertFalse(at.exception,str(at.exception));self.assertEqual(len(calls),2)
    self.assertEqual(next(x.value for x in at.metric if x.label=='Successful Real-Read Cycles'),'1')
    self.assertEqual(next(x.value for x in at.metric if x.label=='Committed Local Paper Trades'),'0')
    at.run();self.assertEqual(len(calls),2)
    next(b for b in at.button if b.label=='Stop Market Monitor').click().run()
    self.assertFalse(at.exception);self.assertFalse(at.session_state['monitor_running']);self.assertEqual(len(calls),2)
    at.run();self.assertEqual(len(calls),2)
    self.assertEqual(next(x.value for x in at.metric if x.label=='Paper Cash'),'$50.00')

if __name__=='__main__':unittest.main(verbosity=2)
