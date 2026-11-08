"""Optional SAME-HOST diagnostic. Fixed supported operational CLI reads only.
The Streamlit app embeds the adapter; this helper is not a required dependency.
No server, loop, key, approval, order or desk-state mutation is implemented.
"""
import json
from trading_terminal import LocalDeskStatus

if __name__=='__main__':
    result=LocalDeskStatus().snapshot()
    print(json.dumps(result,indent=2))
    raise SystemExit(2 if result['desk_state']=='UNSAFE MODE — STOP' else (0 if result['connection']=='CONNECTED READ-ONLY' else 3))
