import os,re,tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
from market_paper_terminal.core import Store,scan
from market_paper_terminal.test_core import fixture
BENGALI=re.compile('[\u0980-\u09ff]')

def verify(app):
 assert not app.exception,app.exception
 for category in ['markdown','caption','text','info','warning','error','success','button','selectbox','number_input','tabs','status','expander']:
  for element in getattr(app,category,[]):
   for attr in ['value','label','options']:
    value=getattr(element,attr,None)
    assert not BENGALI.search(str(value)),(category,attr,value)
 for frame in app.dataframe:
  assert not BENGALI.search(frame.value.to_string())
 for item in app.json:
  assert not BENGALI.search(str(item.value))

with tempfile.TemporaryDirectory() as tmp:
 os.environ['PUMPGROK_TERMINAL_DB']=str(Path(tmp)/'english.db')
 app=AppTest.from_file(str(Path(__file__).resolve().parent.parent/'trading_terminal.py'),default_timeout=30).run();verify(app)
 assert app.metric[0].value=='$50.00'
 markup='\n'.join(x.value for x in app.markdown)
 assert 'Market Scanner v2 • English / Dark' in markup and '#070b14' in markup
 assert markup.count('NOT CONNECTED')==10
 s=Store(os.environ['PUMPGROK_TERMINAL_DB']);scan(s,fixture)
 # Existing localized logs/labels remain stored but must not leak into presentation.
 old='\u0986\u0997\u09c7\u09b0 \u09b2\u0997'
 s.log('CODE / DISCOVERY',old)
 r=s.rows()[0];r['symbol']=old;s.save_rows([r])
 app.run();verify(app)
 assert any(e['message']==old for e in s.events())
 app.button[0].click().run();verify(app)
 next(x for x in app.button if 'Save Research Draft' in x.label).click().run();verify(app)
 assert s.cash()==50 and len(s.tickets())==1
 # Failure state must remain honest and English, with no false successful fetch.
 s.set('health',{'status':'ERROR','utc':None,'error':'HTTP 503: upstream unavailable'})
 app.run();verify(app)
 assert any('503' in w.value for w in app.warning)
 assert s.cash()==50
for path in [Path(__file__).resolve().parent.parent/'trading_terminal.py',Path(__file__).resolve().parent/'core.py']:
 assert not BENGALI.search(Path(path).read_text()),path
print('PASS: English-only rendered controls, logs, tables, JSON, empty/data/error states; legacy evidence retained; dark version marker; all 10 disconnected; no fake cash changes.')
