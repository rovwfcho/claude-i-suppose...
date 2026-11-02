const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const [src, dst] of process.argv.slice(2).map(a => a.split('='))) {
    await p.goto('file://' + src, {waitUntil: 'networkidle'});
    await p.evaluate(() => document.fonts.ready);
    await p.pdf({path: dst, format: 'A4', printBackground: true, preferCSSPageSize: true,
                 displayHeaderFooter: true, headerTemplate: '<span></span>',
                 footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#888;font-family:Inter,sans-serif"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
  }
  await b.close();
})();
