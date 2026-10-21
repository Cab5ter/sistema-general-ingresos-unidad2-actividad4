// Capturas del visor de las peticiones HTTP y consultas SQL reales de activity6_evidence.
const fs = require('fs/promises');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const output = path.resolve(process.env.EVIDENCE_DIR || 'entrega/evidencias-actividad6');
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1100 }, deviceScaleFactor: 1 });
    const files = (await fs.readdir(output)).filter(f => /^\d\d-.*\.html$/.test(f)).sort();
    if (!files.length) throw Error('Ejecuta primero python -m scripts.activity6_evidence');
    for (const file of files) {
      await page.goto(pathToFileURL(path.join(output, file)).href);
      await page.screenshot({ path: path.join(output, file.replace(/\.html$/, '.png')), fullPage: true });
      console.log(file.replace(/\.html$/, '.png'));
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
