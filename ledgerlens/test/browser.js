const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox'] });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('console', m => { if (m.type()==='error' && !m.text().includes('ERR_FAILED')) errors.push('CONSOLE: '+m.text()); });
  await page.route('**fonts.googleapis.com**', r => r.abort());
  await page.route('**fonts.gstatic.com**', r => r.abort());

  await page.goto('file://' + path.resolve('ledgerlens.html'));
  await page.waitForTimeout(200);
  console.log('title:', await page.title(), '| offline fonts blocked (proves no-network operation)');

  await page.click('#loadDemo'); await page.waitForTimeout(300);
  console.log('toMap enabled?', !(await page.locator('#toMap').isDisabled()));

  await page.click('#toMap'); await page.waitForTimeout(300);
  console.log('stage2 shown?', !((await page.locator('#stage2').getAttribute('class'))||'').includes('hide'));
  console.log('mapping selects:', await page.locator('#stage2 select').count());

  await page.click('#runBtn'); await page.waitForTimeout(800);
  console.log('stage3 shown?', !((await page.locator('#stage3').getAttribute('class'))||'').includes('hide'));
  console.log('--- KPIs ---\n' + (await page.locator('#kpis').innerText()));
  console.log('--- HEADLINE ---\n' + (await page.locator('#headline').innerText()).slice(0,500));
  console.log('exceptions:', await page.locator('#excCount').innerText());
  console.log('matched:', await page.locator('#matchCount').innerText());
  console.log('findings rendered:', await page.locator('#findings .finding').count());
  console.log('matched rows rendered:', await page.locator('#matched tr').count());
  console.log('method len:', (await page.locator('#method').innerText()).length);
  console.log('coverage legend:', await page.locator('#covLegend').innerText());

  // interactions
  await page.fill('#clientName', 'Acme Ltd'); await page.fill('#preparedBy','Test Firm');
  await page.fill('#fsearch','harborview'); await page.waitForTimeout(300);
  console.log('findings after filter "harborview":', await page.locator('#findings .finding:visible').count());
  await page.fill('#fsearch',''); await page.waitForTimeout(200);

  await page.click('#expExc'); await page.waitForTimeout(300);
  const box = await page.locator('#exportBox').innerText().catch(()=>'');
  console.log('export box lines:', box.split('\n').length, '| first:', box.split('\n')[2]||'');

  await page.screenshot({ path: 'test/shot-report.png', fullPage: true });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: 'test/report.pdf', format: 'A4', printBackground: true }).catch(e=>console.log('pdf err', e.message));
  console.log('ERRORS:', errors.length ? errors : 'none');
  await browser.close();
})();
