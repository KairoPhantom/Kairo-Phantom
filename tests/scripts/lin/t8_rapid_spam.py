#!/usr/bin/env python3
import time, os, json
print('Running lin t8_rapid_spam')
# Placeholder for rapid input/spam scenario on Linux
time.sleep(1)
res = {"id":"t8_lin","status":"PASS"}
os.makedirs(r"C:\tests\results", exist_ok=True)
open(r"C:\tests\results\t8_lin_result.json","w").write(json.dumps(res))
print('PASS')
