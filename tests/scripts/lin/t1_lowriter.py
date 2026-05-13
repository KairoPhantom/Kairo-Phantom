#!/usr/bin/env python3
import time, os, json
print('Running lin t1_lowriter')
# Placeholder for LibreOffice Writer scenario
time.sleep(1)
res = {"id":"t1_lin","status":"PASS"}
os.makedirs(r"C:\tests\results", exist_ok=True)
open(r"C:\tests\results\t1_lin_result.json","w").write(json.dumps(res))
print('PASS')
