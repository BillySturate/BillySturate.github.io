#!/usr/bin/env python3
"""Optional online check of direct image references. Never imports article text."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'legacy/assets.json').read_text())
    urls = sorted({item['reference'] for item in manifest.values() if 'reference' in item})
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
        page = browser.new_page()
        page.set_content('<!doctype html><meta name="referrer" content="no-referrer"><title>Image verification</title>')
        results = page.evaluate('''async paths => {
          const results = [];
          for (let i = 0; i < paths.length; i += 8) {
            await Promise.all(paths.slice(i, i + 8).map(src => new Promise(resolve => {
              const image = new Image();
              image.referrerPolicy = 'no-referrer';
              let completed = false;
              const finish = status => {
                if (completed) return;
                completed = true;
                clearTimeout(timer);
                results.push({src, status, width: image.naturalWidth, height: image.naturalHeight});
                resolve();
              };
              const timer = setTimeout(() => finish('timeout'), 15000);
              image.onload = () => finish('ok');
              image.onerror = () => finish('error');
              image.src = src;
            })));
          }
          return results;
        }''', urls)
        browser.close()
    report = {'checked': len(results), 'passed': sum(r['status'] == 'ok' for r in results), 'failures': [r for r in results if r['status'] != 'ok'], 'results': results}
    (ROOT / 'reports/csdn-image-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False, indent=2))
    if report['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
