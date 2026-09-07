import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const t = (p) => fs.readFile(new URL(`../${p}`, import.meta.url), 'utf8');

test('v1.6.1 packages native one-click launchers', async () => {
  const pkg = JSON.parse(await t('package.json'));
  assert.equal(pkg.version, '1.6.1-pilot');
  const [bat, sh, ps] = await Promise.all([t('START.bat'), t('start.sh'), t('scripts/one-click-start.ps1')]);
  assert.match(bat, /one-click-start\.ps1/u);
  assert.match(sh, /one-click-start\.sh/u);
  assert.match(ps, /docker compose build/u);
  assert.match(ps, /docker compose up -d/u);
});

test('one-click launchers bootstrap secrets and support offline image', async () => {
  const [sh, ps] = await Promise.all([t('scripts/one-click-start.sh'), t('scripts/one-click-start.ps1')]);
  for (const src of [sh, ps]) {
    assert.match(src, /SCHEDULER_TOKEN/u);
    assert.match(src, /USER_DATA_HMAC_KEY/u);
    assert.match(src, /AUDIT_HMAC_KEY/u);
    assert.match(src, /okno-v-kitai-image\.tar/u);
    assert.match(src, /\.pilot-access\.txt/u);
  }
});
