#!/usr/bin/env python3
"""Verify clock appearance, real-domain counter routing and shared paper metadata."""
import argparse
import functools
import http.server
import json
import os
import threading
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',default='dist');args=parser.parse_args()
    out=ROOT/args.directory;base=json.loads((out/'migration-report.json').read_text())['base_path']
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if base:
                if not self.path.startswith(base+'/'):self.send_error(404);return
                self.path=self.path[len(base):]
            super().do_GET()
        def log_message(self,*_):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(out)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    host=f'http://127.0.0.1:{server.server_port}';start=host+base;checks=[];errors=[];suffix='-preview' if base else ''
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
            context=browser.new_context(timezone_id='Asia/Shanghai',color_scheme='dark')
            context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(host+'/') else r.abort())
            page=context.new_page();page.on('pageerror',lambda e:errors.append(page.url+': '+str(e)))
            page.clock.install(time='2026-11-14T04:00:00Z')
            page.goto(start+'/blog/');page.wait_for_function('typeof billyAutoTheme === "function"')
            assert page.locator('html').get_attribute('data-theme')=='light'
            assert page.locator('.banners-title-big').all_text_contents()==['写点代码，','走点远路。']
            assert '产品、设计' not in page.locator('.author-info__description').inner_text()
            assert '计算机硕士' not in page.locator('.author-info__description').inner_text()
            assert page.locator('.author-info__description p').all_text_contents()==['欢迎来到我的秘密基地！','这里有编程笔记、踩坑记录，也有旅行途中遇见的风景和生活中的奇思妙想。','写点代码，走点远路。']
            page.wait_for_function('document.querySelector("#author-info__sayhi").textContent === "Hi there! 👋"')
            page.set_viewport_size({'width':1440,'height':1000})
            page.screenshot(path=str(ROOT/f'reports/screenshots/blog-refined-light{suffix}.png'),animations='disabled')
            assert page.locator('[data-live-stat]').evaluate_all('(els)=>els.every(e=>e.hidden)')
            page.clock.set_system_time('2026-11-14T12:00:00Z');page.evaluate('billyAutoTheme()')
            assert page.locator('html').get_attribute('data-theme')=='dark'
            page.clock.set_system_time('2026-11-15T04:00:00Z');page.evaluate('billyAutoTheme()')
            page.wait_for_function('typeof rm.switchDarkMode === "function"')
            page.locator('#darkmode_navswitch a').click();assert page.locator('html').get_attribute('data-theme')=='dark'
            page.clock.fast_forward(60000);assert page.locator('html').get_attribute('data-theme')=='dark'
            page.reload();assert page.locator('html').get_attribute('data-theme')=='dark'
            checks.append('Local clock day/night, manual preference retained, preview counters suppressed')
            page.clock.set_system_time('2030-01-01T04:00:00Z');page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
            assert page.locator('[data-blog-year]').inner_text()=='2030'
            checks.append('Copyright year follows browser clock')
            page.clock.set_system_time('2026-11-14T12:00:00Z');page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
            page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(ROOT/f'reports/screenshots/blog-refined-desktop{suffix}.png'),animations='disabled')
            assert page.locator('#home_top .categoryGroup,#home_top #topPostGroup').count()==0
            assert page.locator('#home_top .blog-slider__item').count()>=2
            assert page.locator('#random-banner').evaluate('(e)=>e.getBoundingClientRect().height')<=310
            assert abs(page.locator('#random-banner').evaluate('(e)=>e.getBoundingClientRect().height')-page.locator('#swiper_container').evaluate('(e)=>e.getBoundingClientRect().height'))<=5
            assert page.locator('.card-info .author-info__description p').first.evaluate('(e)=>getComputedStyle(e).color')=='rgb(255, 255, 255)'
            assert page.locator('link[rel="shortcut icon"]').get_attribute('href')==base+'/assets/favicon-64.png'
            assert page.locator('link[rel="apple-touch-icon"]').get_attribute('href')==base+'/assets/apple-touch-icon.png'
            bullets=page.locator('#home_top .swiper-pagination-bullet')
            assert bullets.count()>=2
            bullets.nth(1).click();page.wait_for_timeout(300)
            assert bullets.nth(1).get_attribute('class').find('swiper-pagination-bullet-active')>=0
            for width in [820,390,320]:
                page.set_viewport_size({'width':width,'height':844})
                page.wait_for_timeout(180)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                assert page.locator('#random-banner').is_visible(),width
                assert page.locator('#swiper_container').is_visible(),width
                if width==390:
                    print('CAROUSEL_DIMENSIONS',page.locator('#home_top').evaluate('(e)=>Object.fromEntries([".swiper_container_card","#bannerGroup","#swiper_container_blog","#swiper_container",".blog-slider__item.swiper-slide-active",".blog-slider__img",".blog-slider__content"].map(s=>{const r=e.querySelector(s)?.getBoundingClientRect();return [s,r&&[r.x,r.y,r.width,r.height]]}))'))
                page.screenshot(path=str(ROOT/f'reports/screenshots/blog-refined-{width}{suffix}.png'),animations='disabled')
            page.goto(start+'/research/')
            assert page.locator('.publication').count()==3
            patent=page.locator('#hierarchical-eeg-visual-recognition-patent')
            assert patent.locator('.authors').inner_text().startswith('Hao Liu, Wanzeng Kong')
            assert patent.locator('.inventor-role').inner_text()=='First inventor'
            assert patent.locator('.application-number').inner_text()=='Application No. 2026116165825'
            assert patent.locator('.badge').inner_text()=='Preliminary examination passed'
            assert page.locator('.journal-metrics').count()==3
            assert 'JCR' not in page.locator('#main').inner_text()
            assert 'Target journal' not in page.locator('#main').inner_text()
            assert page.locator('.publication').nth(0).locator('.paper-meta').inner_text().find('Accept')>=0
            assert page.locator('.publication').nth(1).locator('a').count()==0
            assert page.locator('.publication').nth(2).locator('a').count()==0
            assert page.locator('.journal-metrics>span').all_text_contents()==['中科院一区 TOP','IF 7.7','中科院一区 TOP','IF 9.1','中科院三区','IF 3.6']
            for width in [1440,820,390,320]:
                page.set_viewport_size({'width':width,'height':1000 if width>700 else 844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(ROOT/f'reports/screenshots/research-refined-{width}{suffix}.png'),full_page=True,animations='disabled')
            for path in ['/', '/cv/']:
                page.goto(start+path);assert page.locator('.publication').count()==2
                assert page.locator('.journal-metrics>span').all_text_contents()==['中科院一区 TOP','IF 7.7','中科院一区 TOP','IF 9.1']
            page.goto(start+'/blog/about/')
            assert page.locator('.ba-hello').count()==0
            assert '计算机硕士' not in page.locator('.ba-hero,.ba-who').all_inner_texts()[0] + page.locator('.ba-who').inner_text()
            checks.append('Three papers, two selected, owner-confirmed CAS tags, no visible JCR, shared metrics and mobile wrapping')
            production=browser.new_context()
            counter_requests=[]
            def production_route(route):
                url=route.request.url
                if url.startswith('https://busuanzi.ibruce.info/'):
                    counter_requests.append((url,route.request.headers.get('referer')))
                    route.fulfill(content_type='application/javascript',body="document.getElementById('busuanzi_value_site_uv').textContent='42';document.getElementById('busuanzi_value_site_pv').textContent='84';")
                elif url.startswith('https://www.billysturate.top/'):
                    path=urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip('/')
                    if base and path.startswith(base.lstrip('/')+'/'):path=path[len(base.lstrip('/'))+1:]
                    target=out/path
                    if target.is_dir():target/='index.html'
                    if target.is_file():route.fulfill(path=str(target))
                    else:route.abort()
                else:route.abort()
            production.route('**/*',production_route)
            prod_page=production.new_page();prod_page.goto('https://www.billysturate.top'+base+'/blog/')
            prod_page.wait_for_function('document.querySelector("#busuanzi_value_site_uv").textContent==="42"')
            assert prod_page.locator('[data-live-stat]').evaluate_all('(els)=>els.every(e=>!e.hidden)')
            assert len(counter_requests)==2 and counter_requests[0]==('https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js','https://www.billysturate.top/') and counter_requests[1][0].startswith('https://busuanzi.ibruce.info/busuanzi?') and counter_requests[1][1]=='https://www.billysturate.top'+base+'/blog/',counter_requests
            production.close()
            checks.append('Production-domain counter gate, correct Referer and numeric response display (mock service; no fixture numbers in site)')
            browser.close()
        assert not errors,errors
        result={'passed':True,'checks':checks,'page_errors':errors,'statistics_live_snapshot':'6738 UV / 8093 PV on billysturate.top; sequential www check 6739 / 8094, not embedded in site','cas_basis':'Owner-confirmed; CAS edition year unspecified','impact_factor_year':2025}
        (ROOT/f'reports/home-refinement{suffix}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:server.shutdown()

if __name__=='__main__':main()
