const { chromium } = require('playwright');
const path=require('path');
(async()=>{
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
 for (const vp of [{width:390,height:844,n:'mobile'},{width:1280,height:900,n:'desktop'}]) {
   const p=await b.newPage({viewport:{width:vp.width,height:vp.height}});
   await p.route('**fonts.g**',r=>r.abort());
   await p.goto('file://'+path.resolve('ledgerlens.html'));
   await p.click('#loadDemo'); await p.waitForTimeout(250);
   await p.click('#toMap'); await p.waitForTimeout(250);
   await p.click('#runBtn'); await p.waitForTimeout(600);
   const overflow = await p.evaluate(()=>({docW:document.documentElement.scrollWidth, winW:window.innerWidth}));
   console.log(vp.n, 'scrollWidth',overflow.docW,'vs viewport',overflow.winW, overflow.docW>overflow.winW+2 ? '<-- HORIZONTAL OVERFLOW':'ok');
   if(vp.n==='mobile') await p.screenshot({path:'test/shot-mobile.png',fullPage:false});
   await p.close();
 }
 // a11y basics
 const p=await b.newPage(); await p.route('**fonts.g**',r=>r.abort());
 await p.goto('file://'+path.resolve('ledgerlens.html'));
 const a11y = await p.evaluate(()=>{
   const noLabel=[...document.querySelectorAll('input,select,textarea')].filter(e=>!e.getAttribute('aria-label')&&!e.labels?.length&&!e.closest('label')).length;
   return {lang:document.documentElement.lang||'(MISSING)', hasH1:!!document.querySelector('h1'),
     metaViewport:!!document.querySelector('meta[name=viewport]'),
     charset:!!document.querySelector('meta[charset]'),
     inputsWithoutLabel:noLabel, buttons:document.querySelectorAll('button').length};
 });
 console.log('\nA11Y/HEAD:',JSON.stringify(a11y,null,1));
 await b.close();
})();
