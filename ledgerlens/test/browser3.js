const { chromium } = require('playwright');
const path=require('path'), fs=require('fs');
(async()=>{
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
 const p=await b.newPage(); const errs=[];
 p.on('pageerror',e=>errs.push('PAGEERROR: '+e.message));
 await p.route('**fonts.g**',r=>r.abort());
 await p.goto('file://'+path.resolve('ledgerlens.html'));
 fs.writeFileSync('/tmp/junk.txt','this is not a csv at all\njust prose, no delimiters\n');
 await p.locator('#slot-ledger input[type=file]').setInputFiles('/tmp/junk.txt');
 await p.waitForTimeout(600);
 console.log('[junk] slot-ledger text:\n', await p.locator('#slot-ledger').innerText());
 console.log('[junk] loadNote:', await p.locator('#loadNote').innerText());
 console.log('[junk] toast:', await p.locator('#toast').innerText());
 await p.screenshot({path:'test/shot-junk.png', fullPage:true});

 // xlsx file (README says unsupported) - what does the user see?
 fs.writeFileSync('/tmp/book.xlsx', Buffer.from('504b0304140000000800','hex'));
 await p.locator('#slot-bank input[type=file]').setInputFiles('/tmp/book.xlsx');
 await p.waitForTimeout(600);
 console.log('\n[xlsx] slot-bank text:\n', await p.locator('#slot-bank').innerText());
 console.log('[xlsx] toast:', await p.locator('#toast').innerText());

 // very large file guard
 let big='Inv,Date,Amount\n'; for(let i=0;i<120000;i++) big+='I'+i+',2026-06-01,'+(i%900+10)+'.00\n';
 fs.writeFileSync('/tmp/big.csv', big);
 console.log('\nbig.csv size MB:', (fs.statSync('/tmp/big.csv').size/1048576).toFixed(1));
 const t0=Date.now();
 await p.locator('#slot-ledger input[type=file]').setInputFiles('/tmp/big.csv');
 await p.waitForTimeout(3000);
 console.log('[big] slot text after 3s:', (await p.locator('#slot-ledger').innerText()).slice(0,200));
 console.log('[big] elapsed', Date.now()-t0,'ms');
 console.log('\nERRORS:', errs.length?errs:'none');
 await b.close();
})();
