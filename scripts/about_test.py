#!/usr/bin/env python3
"""About layout, navigation, reduced-motion and page isolation checks."""
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
    parser.add_argument('--verify-isolation', action='store_true', help='Compare against the original About-only task baseline')
    args = parser.parse_args()
    out = ROOT / args.directory
    base = json.loads((out / 'migration-report.json').read_text())['base_path']
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if base:
                if not self.path.startswith(base + '/'):
                    self.send_error(404)
                    return
                self.path = self.path[len(base):]
            super().do_GET()
        def log_message(self, *_): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    shots = ROOT / 'reports/screenshots'
    suffix = '-preview' if base else ''
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
            context = browser.new_context()
            context.route('**/*', lambda r: r.continue_() if r.request.url.startswith(origin + '/') else r.abort())
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            # Begin outside About, exercising the retained PJAX navigation.
            page.goto(origin + base + '/blog/')
            link = page.locator('#nav a[href="' + base + '/blog/about/"]')
            link.evaluate('(a)=>a.click()')
            page.wait_for_selector('.ba-hero')
            page.wait_for_function('getComputedStyle(document.querySelector(".ba-grid")).display === "grid"')
            for width in (1440, 820, 390, 320):
                page.set_viewport_size({'width':width, 'height':1000 if width>700 else 844})
                for theme in ('dark', 'light'):
                    page.evaluate('t=>document.documentElement.dataset.theme=t', theme)
                    page.wait_for_timeout(200)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (width, theme)
                    assert page.get_by_role('heading', level=1).inner_text() == "Hi, I'm BillySturate. 👋"
                    assert page.locator('.ba-tech').count() == 8
                    assert page.locator('.ba-keyword').all_text_contents() == ['BCI & EEG', 'Robotics & C++', 'Travel & Explore']
                    assert page.locator('.ba-keyword svg').count() == 3
                    assert page.locator('.ba-intro').inner_text() == '平时研究脑机接口与机器学习，也喜欢折腾机器人、C++ 和各种有意思的工程项目。代码之外，我热爱旅行，喜欢去陌生的城市走走，认识不同的人。'
                    assert page.locator('.ba-who > p').inner_text() == '喜欢琢磨新东西，也享受把想法一步步变成现实的过程。偶尔写写代码，偶尔出去走走，希望一直保有自己的好奇心。'
                    assert page.locator('.ba-timeline li').count() == 3
                    assert page.locator('.ba-travel').count() == 0
                    assert page.locator('.ba-education dd').count() == 2
                    assert '杭州电子科技大学' in page.locator('.ba-education').inner_text()
                    assert '安徽理工大学' in page.locator('.ba-education').inner_text()
                    assert page.locator('.ba-who .ba-education').count() == 0
                    assert page.locator('.ba-education small').all_text_contents() == ['计算机科学与技术'] * 2
                    assert page.locator('.ba-timeline li').nth(2).locator('.ba-eyebrow').inner_text() == "03 / WHAT'S NEXT"
                    assert page.locator('.ba-timeline li').nth(2).locator('p').inner_text() == '对技术和世界依然充满好奇。未来想继续学习新知识，尝试有趣的项目，也去更多地方走走看看。至于下一站会在哪里，就交给时间慢慢回答。'
                    assert page.locator('.ba-timeline li').nth(2).locator('.ba-eyebrow').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
                    assert page.locator('.ba-timeline li').nth(2).locator('.ba-eyebrow').evaluate('(e)=>e.getBoundingClientRect().height<30')
                    who, build, education, personality = page.evaluate("['.ba-who','.ba-build','.ba-education-strip','.ba-personality'].map(s=>document.querySelector(s).getBoundingClientRect().toJSON())")
                    if width > 700:
                        assert abs(who['height']-build['height']) < 2
                        assert abs(who['y']-build['y']) < 2
                        assert who['height'] < 410
                        assert education['height'] < 175
                    else:
                        assert build['y'] >= who['y']+who['height']
                        assert education['height'] < 230
                    assert 12 <= education['y']-(build['y']+build['height']) <= 24
                    assert 12 <= personality['y']-(education['y']+education['height']) <= 24
                    assert page.locator('.ba-gallery').count() == 0
                    assert page.locator('#about-page').inner_text().count('Stay curious.') == 1
                    for img in page.locator('#about-page img').all():
                        img.evaluate('(i)=>i.decode()')
                        assert img.evaluate('(i)=>i.naturalWidth>10')
                    assert page.locator('.ba-card').first.evaluate('(e)=>getComputedStyle(e).borderTopStyle') == 'solid'
                    page.screenshot(path=str(shots / f'about-v2-{width}-{theme}{suffix}.png'), full_page=True, animations='disabled')
                    checks.append(f'{width}px {theme}: grid, images, no overflow')
                if width == 390:
                    for name in ('personality', 'journey', 'story'):
                        card = page.locator('.ba-' + name)
                        card.scroll_into_view_if_needed()
                        assert card.is_visible()
                        page.screenshot(path=str(shots / f'about-v2-mobile-{name}{suffix}.png'), animations='disabled')
                    page.evaluate('scrollTo(0,0)')
            page.emulate_media(reduced_motion='reduce')
            assert page.locator('.ba-hero').evaluate('(e)=>getComputedStyle(e).animationName') == 'none'
            assert page.locator('.ba-stars').evaluate('(e)=>getComputedStyle(e).pointerEvents') == 'none'
            assert page.get_by_role('navigation', name='About links').get_by_role('link').count() == 4
            for a in page.locator('#about-page a[href^="/"]').all():
                response = context.request.get(origin + a.get_attribute('href'))
                assert response.ok
            # Academic link bypasses PJAX; returning to blog restores its shell.
            page.get_by_role('link', name='Visit my academic homepage').click()
            page.wait_for_selector('.portrait')
            assert page.locator('h1').inner_text().startswith('Hao Liu')
            assert page.locator('.ba-stars').count() == 0
            checks.append('Reduced motion, contact links, PJAX entry and academic-home exit')
            browser.close()
        assert not errors, errors
        isolation = []
        if args.verify_isolation and not base and (ROOT / 'backups/about-baseline.json').exists():
            baseline = json.loads((ROOT / 'backups/about-baseline.json').read_text())
            for name, digest in baseline.items():
                if name in ('blog/about/index.html',): continue
                assert (out / name).is_file(), name
                assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest, name
                isolation.append(name)
        report = {'passed':True,'checks':checks,'page_errors':errors,'existing_non_about_files_identical':len(isolation)}
        (ROOT / f'reports/about-v2{suffix}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        server.shutdown()

if __name__ == '__main__': main()
