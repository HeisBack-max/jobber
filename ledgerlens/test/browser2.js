const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const T = [];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox'] });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await page.route('**fonts.g**', r => r.abort());
  await page.goto('file://' + path.resolve('ledgerlens.html'));
  await page.waitForTimeout(200);

  // Load the two REAL sample CSVs through the file inputs
  const inputs = page.locator('input[type=file]');
  console.log('file inputs found:', await inputs.count());
  await page.locator('#slot-ledger input[type=file]').setInputFiles('samples/sample-invoices.csv');
  await page.waitForTimeout(400); await page.locator('#slot-bank input[type=file]').setInputFiles('samples/sample-bank-statement.csv');
  await page.waitForTimeout(500);
  console.log('toMap enabled after real files?', !(await page.locator('#toMap').isDisabled()));
  await page.click('#toMap'); await page.waitForTimeout(300);

  // dump the guessed mapping shown to the user
  const sels = await page.locator('#stage2 select').all();
  for (const s of sels) console.log('  select', await s.getAttribute('id'), '=', await s.inputValue());

  await page.click('#runBtn'); await page.waitForTimeout(600);
  console.log('real-file report exceptions:', await page.locator('#excCount').innerText());
  console.log('currency shown in header:', await page.locator('#period').innerText());

  // --- failure path: garbage file ---
  const p2 = await ctx.newPage();
  p2.on('pageerror', e => errs.push('PAGEERROR(garbage): ' + e.message));
  await p2.route('**fonts.g**', r => r.abort());
  await p2.goto('file://' + path.resolve('ledgerlens.html'));
  fs.writeFileSync('/tmp/junk.txt', 'this is not a csv at all\njust prose, no delimiters\n');
  fs.writeFileSync('/tmp/nohdr.csv', 'Widget,Colour\nbolt,red\nnut,blue\n');
  const i2 = p2.locator('input[type=file]');
  await p2.locator('#slot-ledger input[type=file]').setInputFiles('/tmp/junk.txt');
  await p2.waitForTimeout(400); await p2.locator('#slot-bank input[type=file]').setInputFiles('/tmp/nohdr.csv');
  await p2.waitForTimeout(500);
  console.log('\n[garbage] toMap enabled?', !(await p2.locator('#toMap').isDisabled()));
  if (!(await p2.locator('#toMap').isDisabled())) {
    await p2.click('#toMap'); await p2.waitForTimeout(300);
    await p2.click('#runBtn'); await p2.waitForTimeout(600);
    console.log('[garbage] runNote:', await p2.locator('#runNote').innerText().catch(()=>''));
    console.log('[garbage] stage3 shown?', !((await p2.locator('#stage3').getAttribute('class'))||'').includes('hide'));
    console.log('[garbage] toast:', await p2.locator('#toast').innerText().catch(()=>''));
    await p2.screenshot({path:'test/shot-garbage.png', fullPage:true});
  }
  console.log('\nERRORS:', errs.length ? errs : 'none');
  await browser.close();
})();
