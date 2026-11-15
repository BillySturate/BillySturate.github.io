#!/usr/bin/env python3
"""Check navigation, the original AC interactions and responsive Playground."""
import argparse
import functools
import hashlib
import http.server
import json
import os
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='dist')
    args = parser.parse_args()
    out = ROOT / args.directory
    base = json.loads((out / 'migration-report.json').read_text())['base_path']
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if base:
                if not self.path.startswith(base + '/'):
                    self.send_error(404); return
                self.path = self.path[len(base):]
            super().do_GET()
        def log_message(self, *_): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    start = origin + base
    errors, failed, checks = [], [], []
    suffix = '-preview' if base else ''
    shots = ROOT / 'reports/screenshots'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
            context = browser.new_context(viewport={'width':1440,'height':1000})
            context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(origin + '/') else r.abort())
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: failed.append(r.url) if r.url.startswith(origin) and r.status>=400 else None)
            page.goto(start + '/')
            assert page.get_by_role('navigation',name='Main navigation').get_by_role('link',name='Blog',exact=True).count()==1
            page.get_by_role('navigation',name='Main navigation').get_by_role('link',name='Blog',exact=True).click()
            page.wait_for_selector('#nav .blog-academic-nav')
            menu = page.locator('#nav .menus_items')
            assert [s.strip() for s in menu.locator(':scope > .menus_item > a').all_text_contents()]==['文章','友链','小玩意','关于','个人主页 ↗']
            assert menu.locator('a[href$="/air-conditioner/"]').count()==0
            menu.get_by_role('link',name='小玩意',exact=True).click()
            page.wait_for_selector('#playground-page')
            assert page.locator('.pg-card').count()==1
            assert page.locator('.pg-art img').evaluate('(i)=>i.complete && i.naturalWidth>0')
            page.evaluate('document.documentElement.dataset.theme="dark"')
            page.screenshot(path=str(shots/f'playground-desktop{suffix}.png'),full_page=True,animations='disabled')
            page.get_by_role('link',name='进入体验').click()
            page.wait_for_selector('button[aria-label="开关空调"]')
            assert page.locator('.temperature').inner_text()=='26'
            page.get_by_role('button',name='开关空调',exact=True).click()
            page.wait_for_function('document.querySelector(".air-conditioner-wind").classList.contains("windRunningAnimation")')
            page.get_by_role('button',name='制热',exact=True).click()
            assert page.locator('.air-conditioner-main-content-subject-right-mode').inner_text()=='☀️'
            page.get_by_role('button',name='制冷',exact=True).click()
            assert page.locator('.air-conditioner-main-content-subject-right-mode').inner_text()=='❄️'
            page.get_by_role('button',name='升高温度',exact=True).click()
            assert page.locator('.temperature').inner_text()=='27'
            page.get_by_role('button',name='降低温度',exact=True).click()
            assert page.locator('.temperature').inner_text()=='26'
            for _ in range(20): page.get_by_role('button',name='升高温度',exact=True).click()
            assert page.locator('.temperature').inner_text()=='31'
            for _ in range(20): page.get_by_role('button',name='降低温度',exact=True).click()
            assert page.locator('.temperature').inner_text()=='16'
            page.wait_for_function('[...document.querySelectorAll("#air-conditioner-vue audio")].every(a=>a.readyState>=1)')
            assert page.locator('.air-conditioner-main-content-bottom-logo').evaluate('(i)=>i.complete && i.naturalWidth>0')
            page.get_by_role('button',name='开关空调',exact=True).click()
            assert 'windRunningAnimation' not in page.locator('.air-conditioner-wind').get_attribute('class')
            page.screenshot(path=str(shots/f'air-conditioner-desktop{suffix}.png'),full_page=True,animations='disabled')
            checks.append('Original power, heating/cooling, temperature 16–31, audio metadata and logo')
            for width in (820,390,320):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if width==390:page.screenshot(path=str(shots/f'air-conditioner-mobile{suffix}.png'),full_page=True,animations='disabled')
                checks.append(f'AC layout {width}px')
            page.get_by_role('button',name='开关空调',exact=True).click()
            page.locator('.pg-back').click()
            page.wait_for_selector('#playground-page')
            page.wait_for_timeout(9000)  # The original component starts its fan after 8s.
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(shots/f'playground-mobile{suffix}.png'),full_page=True,animations='disabled')
            page.locator('#toggle-menu').click()
            home = page.locator('#sidebar-menus .blog-academic-nav a')
            assert home.is_visible()
            assert home.get_attribute('href')==base+'/'
            home.click()
            page.wait_for_selector('.portrait')
            assert page.locator('h1').inner_text().startswith('Hao Liu')
            checks.append('Mobile drawer academic-home link, bidirectional navigation, safe widget exit')
            # Direct URL must retain the original component as well as PJAX entry.
            page.goto(start + '/blog/air-conditioner/')
            page.wait_for_selector('button[aria-label="开关空调"]')
            page.get_by_role('button',name='开关空调',exact=True).click()
            assert 'windRunningAnimation' in page.locator('.air-conditioner-wind').get_attribute('class')
            browser.close()
        assert not errors, errors
        assert not failed, failed
        unchanged = 0
        if not base:
            baseline = json.loads((ROOT/'backups/playground-baseline.json').read_text())
            for name,digest in baseline.items():
                if name not in ('index.html','404.html','robots.txt','.nojekyll') and not name.startswith(('assets/','research/','projects/','cv/')):continue
                assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,name
                unchanged+=1
        result={'passed':True,'checks':checks,'page_errors':errors,'local_http_errors':failed,'academic_and_shared_files_unchanged':unchanged}
        (ROOT/f'reports/playground{suffix}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:server.shutdown()

if __name__=='__main__':main()
