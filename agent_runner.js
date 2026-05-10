const { execSync, spawn } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

const PLATFORM = process.argv[2] || 'win'; // 'win', 'mac', 'lin'
const TESTS = (process.argv[3] || 'all').split(',');

function runScript(scriptPath) {
  console.log(`[${PLATFORM}] Running: ${scriptPath}`);
  try {
    execSync(`python ${scriptPath}`, { stdio: 'inherit' });
    return true;
  } catch (e) {
    console.error(`[${PLATFORM}] FAILED: ${scriptPath}`);
    return false;
  }
}

function runBrowserScript(scriptPath) {
  console.log(`[${PLATFORM}] Running browser: ${scriptPath}`);
  try {
    execSync(`node ${scriptPath}`, { stdio: 'inherit' });
    return true;
  } catch (e) {
    console.error(`[${PLATFORM}] FAILED: ${scriptPath}`);
    return false;
  }
}

// Ensure fixtures exist
const fixtureSetupPath = path.join(__dirname, 'tests', 'scripts', 'setup_fixtures.py');
if (fs.existsSync(fixtureSetupPath)) {
    console.log(`[${PLATFORM}] Setting up fixtures...`);
    runScript(fixtureSetupPath);
}

// Start chaos
const chaosCmd = PLATFORM === 'win' 
    ? 'powershell tests/scripts/win/chaos_advanced.ps1' 
    : `bash tests/scripts/${PLATFORM}/chaos_advanced.sh`;

const chaos = spawn(chaosCmd, [], { shell: true, detached: true });
console.log(`[${PLATFORM}] Chaos monkey started.`);

const BASE = `tests/scripts/${PLATFORM}`;
const results = [];

const testsToRun = TESTS[0] === 'all' ? ['t1', 't4'] : TESTS; // Default to currently implemented

for (const testId of testsToRun) {
  let passed = false;
  const id = testId.trim().toLowerCase();
  
  if (id === 't1') {
      const ext = PLATFORM === 'win' ? 'word' : PLATFORM === 'mac' ? 'pages' : 'lowriter';
      passed = runScript(`${BASE}/t1_${ext}.py`);
  } else if (id === 't4') {
      passed = runBrowserScript('tests/scripts/browser/t4_yjs_google_docs.js');
  } else {
      console.log(`[${PLATFORM}] Test ${id} not yet implemented for physical runner.`);
      continue;
  }
  
  results.push({ test: id, passed });
}

// Kill Chaos monkey
try {
  if (os.platform() === 'win32') {
    execSync(`taskkill /pid ${chaos.pid} /t /f`);
  } else {
    process.kill(-chaos.pid, 'SIGTERM');
  }
} catch (e) {
  console.log(`[${PLATFORM}] Chaos monkey shutdown gracefully.`);
}

console.log(JSON.stringify(results, null, 2));
const success = results.every(r => r.passed);
if (!success) {
    console.error(`[${PLATFORM}] GAUNTLET FAILED.`);
    process.exit(1);
} else {
    console.log(`[${PLATFORM}] GAUNTLET PASSED.`);
    process.exit(0);
}
