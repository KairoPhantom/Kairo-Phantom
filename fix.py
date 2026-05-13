import re
with open('orchestrate_39_scenarios_parallel.ps1', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\"^python \", \"\"', \"'^python ', ''\")
content = re.sub(r'\$exitCode = \$job\.Job\.State -eq \"Completed\" \? 0 : 1',
                 'if ($job.Job.State -eq \"Completed\") { $exitCode = 0 } else { $exitCode = 1 }', content)

content = re.sub(r'\$passRate = \$totalScenarios -gt 0 \? \(\$totalPassed / \$totalScenarios \* 100\) : 0',
                 'if ($totalScenarios -gt 0) { $passRate = ($totalPassed / $totalScenarios * 100) } else { $passRate = 0 }', content)

content = re.sub(r'\$status = \$\_\.exitCode -eq 0 \? \"\+ PASS\" : \"x FAIL\"',
                 'if ($_.exitCode -eq 0) { $status = \"+ PASS\" } else { $status = \"x FAIL\" }', content)

with open('orchestrate_39_scenarios_parallel.ps1', 'w', encoding='utf-8') as f:
    f.write(content)
