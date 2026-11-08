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
   with patch.dict(os.environ,{'PUMPGROK_TERMINAL_DB':str(root/'TEST_ONLY.sqlite')},clear=False):
    at=AppTest.from_file(str(root/'trading_terminal.py'),default_timeout=30).run()
    self.assertEqual(len(at.exception),0,str(at.exception))
    labels=[x.label for x in at.metric];self.assertIn('Paper Cash',labels)
    self.assertEqual(next(x.value for x in at.metric if x.label=='Paper Cash'),'$50.00')
    self.assertEqual(next(x.value for x in at.metric if x.label=='Realized P&L'),'$0.00')
    text='\n'.join(str(x.value) for x in at.markdown)
    self.assertIn('Paper System v3',text);self.assertIn('NOT CONNECTED',text);self.assertIn('#070b14',text)
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
    with patch.dict(os.environ,{'PUMPGROK_TERMINAL_DB':f.ledger.path},clear=False):
     at=AppTest.from_file(str(root/'trading_terminal.py'),default_timeout=30).run()
     self.assertEqual(len(at.exception),0,str(at.exception))
     approve=next(b for b in at.button if b.label=='Approve Exact Paper Ticket')
     place=next(b for b in at.button if b.label=='Place Approved Simulated Order ONCE')
     self.assertTrue(approve.disabled);self.assertTrue(place.disabled)
     self.assertTrue(any('NO FILL:' in str(x.value) for x in at.error))
     self.assertEqual(len(f.ledger.snapshot()[1]['fills']),0)
  finally:f.cleanup()

if __name__=='__main__':unittest.main(verbosity=2)
