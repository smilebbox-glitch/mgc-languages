import fs from 'node:fs';
let failures = 0;
const pass = (m) => console.log(`PASS  ${m}`);
const fail = (m) => { console.error(`FAIL  ${m}`); failures++; };
const check = (cond, m) => cond ? pass(m) : fail(m);
const text = (p) => fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';

const pkg = JSON.parse(text('package.json'));
check(pkg.version === '1.6.1-pilot', 'package version is v1.6.1 pilot');
for (const f of ['START.bat','STOP.bat','STATUS.bat','start.sh','stop.sh','status.sh','ONE_CLICK_DEPLOYMENT.md']) {
  check(fs.existsSync(f), `${f} packaged`);
}
for (const f of ['scripts/one-click-start.sh','scripts/one-click-stop.sh','scripts/one-click-status.sh','scripts/one-click-start.ps1','scripts/one-click-stop.ps1','scripts/one-click-status.ps1']) {
  check(fs.existsSync(f), `${f} packaged`);
}
const sh = text('scripts/one-click-start.sh');
const ps = text('scripts/one-click-start.ps1');
check(/\.env\.example[\s\S]*\.env/.test(sh) && /\.env\.example[\s\S]*\.env/.test(ps), 'launchers bootstrap .env');
check(/SCHEDULER_TOKEN/.test(sh) && /USER_DATA_HMAC_KEY/.test(sh) && /AUDIT_HMAC_KEY/.test(sh), 'Linux launcher generates required secrets');
check(/SCHEDULER_TOKEN/.test(ps) && /USER_DATA_HMAC_KEY/.test(ps) && /AUDIT_HMAC_KEY/.test(ps), 'Windows launcher generates required secrets');
check(/docker compose build/.test(sh) && /docker compose up -d/.test(sh), 'Linux launcher builds and starts Compose');
check(/docker compose build/.test(ps) && /docker compose up -d/.test(ps), 'Windows launcher builds and starts Compose');
check(/okno-v-kitai-image\.tar/.test(sh) && /docker load/.test(sh) && /docker image inspect/.test(sh) && /--no-build/.test(sh), 'Linux offline image path validates tag and skips build');
check(/okno-v-kitai-image\.tar/.test(ps) && /docker load/.test(ps) && /docker image inspect/.test(ps) && /--no-build/.test(ps), 'Windows offline image path validates tag and skips build');
check(/healthy/.test(sh) && /healthy/.test(ps), 'launchers wait for healthy state');
check(/\.pilot-access\.txt/.test(sh) && /\.pilot-access\.txt/.test(ps), 'launchers produce local access file');
check(!/Convert\]::ToHexString|Convert::ToHexString/.test(ps) && /RandomNumberGenerator/.test(ps), 'Windows launcher uses PowerShell 5.1-compatible cryptographic RNG');
check(text('.dockerignore').includes('.pilot-access.txt') && text('.gitignore').includes('.pilot-access.txt'), 'generated access file excluded from package/build context');
check(text('.dockerignore').includes('.env') && text('.gitignore').includes('.env'), 'runtime .env excluded from package/build context');

if (failures) {
  console.error(`\n${failures} one-click preflight failure(s).`);
  process.exit(1);
}
console.log('\nOne-click preflight passed.');
