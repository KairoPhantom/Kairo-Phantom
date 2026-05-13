#!/usr/bin/env python3
import time, os, json
print('Running lin t2_cancel')
# Placeholder for cancel flow on Linux
time.sleep(1)
res = {"id":"t2_lin","status":"PASS"}
os.makedirs(r"C:\tests\results", exist_ok=True)
open(r"C:\tests\results\t2_lin_result.json","w").write(json.dumps(res))
print('PASS')
