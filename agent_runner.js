const { execSync, spawn } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

const PLATFORM = process.argv[2] || 'win'; // 'win', 'mac', 'lin'
const TESTS = (process.argv[3] || 'all').split(',');

function runCommand(command) {
  console.log(`[${PLATFORM}] Running: ${command}`);
  try {
    execSync(command, { stdio: 'inherit', shell: true });
    return true;
  } catch (e) {
    console.error(`[${PLATFORM}] FAILED: ${command}`);
    return false;
  }
}

// Ensure fixtures exist
const fixtureSetupPath = path.join(__dirname, 'tests', 'scripts', 'setup_fixtures.py');
if (fs.existsSync(fixtureSetupPath)) {
    console.log(`[${PLATFORM}] Setting up fixtures...`);
    runCommand(`python ${fixtureSetupPath}`);
}

const manifestPath = path.join(__dirname, 'test_manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const platformManifest = manifest[PLATFORM] || [];
const manifestById = new Map(platformManifest.map((entry) => [entry.id.toLowerCase(), entry.cmd]));

// Start chaos
const chaosCmd = PLATFORM === 'win' 
  ? 'powershell -File tests/scripts/win/chaos_advanced.ps1' 
    : `bash tests/scripts/${PLATFORM}/chaos_advanced.sh`;

const chaos = spawn(chaosCmd, [], { shell: true, detached: true });
console.log(`[${PLATFORM}] Chaos monkey started.`);

const BASE = `tests/scripts/${PLATFORM}`;
const results = [];

const testsToRun = TESTS[0] === 'all'
  ? platformManifest.map((entry) => entry.id)
  : TESTS;

for (const testId of testsToRun) {
  let passed = false;
  const id = testId.trim().toLowerCase();

  const command = manifestById.get(id);
  if (!command) {
      console.log(`[${PLATFORM}] Test ${id} not present in ${manifestPath}.`);
      results.push({ test: id, passed: false, skipped: true });
      continue;
  }

  passed = runCommand(command);
  
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
