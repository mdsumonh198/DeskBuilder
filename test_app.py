import os,tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
from market_paper_terminal.core import Store,scan
from market_paper_terminal.test_core import fixture
with tempfile.TemporaryDirectory() as tmp:
 os.environ['PUMPGROK_TERMINAL_DB']=str(Path(tmp)/'ui.sqlite3')
 app=AppTest.from_file(str(Path(__file__).resolve().parent.parent/'trading_terminal.py'),default_timeout=30).run()
 assert not app.exception,app.exception
 assert app.metric[0].value=='$50.00'
 assert any('IDLE' in m.value for m in app.markdown)
 assert any('EXECUTION LOCKED' in x.value for x in app.markdown)
 s=Store(os.environ['PUMPGROK_TERMINAL_DB']);scan(s,fixture)
 app.run();assert not app.exception,app.exception
 app.button[0].click().run();assert not app.exception,app.exception # cached, no network
 assert s.cash()==50 and len(s.rows())==1
 # Research form cannot execute, even when explicitly saved twice.
 form_button=next(x for x in app.button if 'Research Draft' in x.label)
 form_button.click().run();assert not app.exception,app.exception
 next(x for x in app.button if 'Research Draft' in x.label).click().run()
 assert not app.exception,app.exception
 assert len(s.tickets())==1 and s.cash()==50
 assert all(x['status'].startswith('RESEARCH DRAFT') for x in s.tickets())
 print('PASS AppTest idle/locked, cached real-data path, exact-mint draft, duplicate draft idempotency, no fills/cash changes.')
