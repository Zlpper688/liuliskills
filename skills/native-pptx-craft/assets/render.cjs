// 批量渲染 svg_final/*.svg → preview/*.png（Playwright，1.5x）
// 用法：node render.cjs [文件名过滤]
// 依赖：npm i playwright（或全局安装后用 NODE_PATH 指向 node_modules）
// 注意：ESM 的 import 会忽略 NODE_PATH，所以这里用 CommonJS require('playwright')。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 项目根目录：默认当前目录（需含 svg_final/），可用第一个参数前的环境变量覆盖
const ROOT = process.env.DECK_ROOT || process.cwd();
const DIR = path.join(ROOT, 'svg_final');
const OUT = path.join(ROOT, 'preview');

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const files = fs.readdirSync(DIR).filter(f => f.endsWith('.svg')).sort();
  const only = process.argv[2];
  const list = only ? files.filter(f => f.includes(only)) : files;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });

  for (const f of list) {
    const svg = fs.readFileSync(path.join(DIR, f), 'utf8');
    await page.setContent(
      `<html><body style="margin:0;background:#fff">${svg}</body></html>`,
      { waitUntil: 'load' }
    );
    await page.waitForTimeout(350);
    const out = path.join(OUT, f.replace('.svg', '.png'));
    await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1280, height: 720 } });
    console.log('rendered', path.basename(out));
  }
  await browser.close();
})();
