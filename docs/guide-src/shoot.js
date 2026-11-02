const {chromium} = require('playwright');
const fs = require('fs');
(async () => {
  const specs = JSON.parse(fs.readFileSync(process.argv[2]));
  const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist']});
  const p = await b.newPage({viewport: {width: 1400, height: 900}});
  await p.goto('http://127.0.0.1:8766/scene.html');
  await p.waitForFunction(() => window.READY === true);
  const res = {};
  for (const [name, spec] of Object.entries(specs)) {
    const r = await p.evaluate(s => window.render(s), spec);
    fs.writeFileSync(name + '.png', Buffer.from(r.img.split(',')[1], 'base64'));
    res[name] = {labels: r.labels, w: spec.w || 1400, h: spec.h || 900};
  }
  fs.writeFileSync('labels.json', JSON.stringify(res));
  await b.close();
})();
