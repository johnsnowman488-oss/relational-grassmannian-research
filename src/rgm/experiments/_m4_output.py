"""Shared JSON output helper for M4 preliminary job runners."""
import json
import sys

def emit_json(payload):
    text=json.dumps(payload,sort_keys=True,indent=2)
    print(text)
    if len(sys.argv)>1:
        with open(sys.argv[1],"w",encoding="utf-8") as stream: stream.write(text+"\n")
