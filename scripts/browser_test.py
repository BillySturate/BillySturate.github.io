#!/usr/bin/env python3
"""Real Chromium checks against the final artifact, at root or a Pages project path."""
import argparse
import functools
import http.server
import json
import os
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='dist')
    args = parser.parse_args()
    out = ROOT / args.directory
    report = json.loads((out / 'migration-report.json').read_text())
    prefix = report['base_path']

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if prefix:
                if not self.path.startswith(prefix + '/'):
                    self.send_error(404)
                    return
                self.path = self.path[len(prefix):]
            super().do_GET()
        def log_message(self, *_):
            pass
        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Browser navigation and header-only probes can cancel downloads.

    class Server(http.server.ThreadingHTTPServer):
        request_queue_size = 128
    server = Server(('127.0.0.1', 0), functools.partial(Handler, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host = f'http://127.0.0.1:{server.server_port}'
    start = host + prefix
    shots = ROOT / 'reports/screenshots'
    shots.mkdir(exist_ok=True)
    results = {'base_path': prefix, 'external_network_disabled': True, 'http_article_checks': 0, 'http_redirect_checks': 0, 'page_errors': [], 'local_http_errors': [], 'external_failures': [], 'checks': []}
    try:
        posts = json.loads((out / 'blog/search.json').read_text())
        for post in posts:
            with urllib.request.urlopen(start + '/blog/' + urllib.parse.quote(post['path'], safe='/')) as response:
                assert response.status == 200
                results['http_article_checks'] += 1
        for redirect in json.loads((ROOT / 'reports/redirects.json').read_text()):
            with urllib.request.urlopen(start + urllib.parse.quote(redirect['from'], safe='/')) as response:
                assert response.status == 200
                results['http_redirect_checks'] += 1
        with sync_playwright() as p:
            browser = p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL') or None)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1, color_scheme='light')
            # Core pages and cached legacy assets must work independently of old third-party services.
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(host + '/') else route.abort())
            page = context.new_page()
            page.on('pageerror', lambda e: results['page_errors'].append({'url': page.url, 'message': str(e), 'stack': e.stack}))
            page.on('response', lambda r: results['local_http_errors'].append({'url': r.url, 'status': r.status}) if r.url.startswith(host) and r.status >= 400 else None)
            page.on('requestfailed', lambda r: results['external_failures'].append({'url': r.url, 'failure': r.failure}) if not r.url.startswith(host) else None)
            def visit(path):
                page.goto(start + path, wait_until='load')
                page.wait_for_timeout(250)
            def fits(label):
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Horizontal overflow: {label}'
                results['checks'].append(label)
            def featured_slider_works(label):
                page.wait_for_function('document.querySelector("#swiper_container")?.dataset.billySliderFixed === "true"')
                page.wait_for_function('''() => {
                  const slide=document.querySelector('#swiper_container .swiper-slide-active');
                  return slide && Number(getComputedStyle(slide.querySelector('img')).opacity)>.9 && Number(getComputedStyle(slide.querySelector('.blog-slider__title')).opacity)>.9;
                }''')
                active = page.locator('#swiper_container .blog-slider__item.swiper-slide-active')
                assert active.count() == 1
                assert active.locator('img').evaluate('(i) => i.complete && i.naturalWidth > 10')
                assert active.locator('.blog-slider__title').is_visible()
                assert active.evaluate('e => {const a=e.getBoundingClientRect(), c=document.querySelector("#swiper_container").getBoundingClientRect(); return a.left>=c.left-2 && a.right<=c.right+2}')
                results['checks'].append(label + ' featured article visible inside carousel')
            visit('/')
            assert page.locator('h1').inner_text().startswith('Hao Liu')
            assert 'Silas Liu' not in page.locator('body').inner_text()
            assert page.get_by_role('navigation', name='Main navigation').get_by_role('link').count() == 5
            def research_records(full=True):
                page.wait_for_selector('.publication')
                assert page.locator('.publication').count() == (3 if full else 2)
                roles = ['First author', 'First author', 'Second author'] if full else ['First author', 'First author']
                statuses = ['Published', 'Under review', 'Major revision'] if full else ['Published', 'Under review']
                assert page.locator('.author-role').all_text_contents() == roles
                assert page.locator('.publication .badge').all_text_contents() == statuses
                assert page.locator('.publication .self-author').all_text_contents() == ['Hao Liu'] * len(roles)
                assert page.locator('.patent-application').count() == (3 if full else 0)
                if full:
                    assert page.locator('.inventor-role').all_text_contents() == ['First student inventor', 'First inventor', 'Second student inventor']
                    assert page.locator('.patent-application .self-author').all_text_contents() == ['Hao Liu'] * 3
                    assert page.locator('.application-number').all_text_contents() == ['Application No. 202610576996.3', 'Application No. 2026116165825']
            def honors_records():
                assert page.locator('.honor').count() == 2
                assert page.locator('.honor h3').all_text_contents() == ['National Scholarship for Graduate Students', 'China Robot Competition & RoboCup China Open']
                assert page.locator('#robocup-national-second-prize .badge').inner_text() == 'National Second Prize'
                assert page.locator('#robocup-national-second-prize p').inner_text() == '3D Soccer Simulation League'
                labels=page.locator('.honors-list .badge')
                assert labels.evaluate_all('(els)=>els.every(e=>{const a=getComputedStyle(e),b=getComputedStyle(els[0]);return ["height","borderRadius","borderWidth","fontSize","fontWeight","paddingLeft","paddingRight","color","backgroundColor"].every(k=>a[k]===b[k])})')
                before=page.locator('html').get_attribute('data-theme')
                for theme in ('light','dark'):
                    page.locator('html').evaluate('(e,t)=>e.dataset.theme=t',theme)
                    assert labels.evaluate_all('(els)=>els.every(e=>getComputedStyle(e).color===getComputedStyle(els[0]).color && getComputedStyle(e).borderTopWidth==="1px")')
                page.locator('html').evaluate('(e,t)=>e.dataset.theme=t',before)
            def clean_copy():
                text = page.locator('body').inner_text().lower()
                for phrase in ('to be added', 'details pending', 'a project direction', 'after verification', 'no claims are made', 'computing-related discipline', 'will be added here'):
                    assert phrase not in text, f'Development placeholder on {page.url}: {phrase}'
            research_records(full=False)
            honors_records()
            clean_copy()
            assert page.locator('.interests > div > span').count() == 4
            assert page.get_by_role('link', name='billysturate@gmail.com', exact=True).get_attribute('href') == 'mailto:billysturate@gmail.com'
            assert page.locator('.portrait img').evaluate('(i) => i.complete && i.naturalWidth === 1122')
            assert page.locator('#main > .section').evaluate_all('(els) => els.map(e => e.getAttribute("aria-labelledby"))') == ['research-title', 'projects-title', 'honors-title', 'blog-title']
            results['checks'].append('Concise homepage: selected papers, real avatar, contact email, four interests and two honors without years')
            results['typography'] = page.locator('.intro-prose p').first.evaluate('(e) => ({font: getComputedStyle(e).fontFamily, size: getComputedStyle(e).fontSize})')
            assert 'PingFang SC' in results['typography']['font']
            assert float(results['typography']['size'].removesuffix('px')) >= 16
            cdp = context.new_cdp_session(page)
            cdp.send('DOM.enable')
            cdp.send('CSS.enable')
            root_node = cdp.send('DOM.getDocument')['root']['nodeId']
            text_node = cdp.send('DOM.querySelector', {'nodeId': root_node, 'selector': '.intro-prose p'})['nodeId']
            results['typography']['rendered_fonts'] = cdp.send('CSS.getPlatformFontsForNode', {'nodeId': text_node})['fonts']
            cdp.detach()
            fits('Desktop homepage')
            suffix = '-production' if report['production'] else ('-preview' if prefix else '')
            page.screenshot(path=str(shots / f'home-desktop{suffix}.png'), full_page=True)
            page.get_by_role('button', name='Switch to dark mode').click()
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            page.reload()
            assert page.locator('html').get_attribute('data-theme') == 'dark'
            page.screenshot(path=str(shots / f'home-dark{suffix}.png'), full_page=True)
            page.get_by_role('navigation').get_by_role('link', name='Research', exact=True).click()
            research_records()
            page.get_by_role('navigation', name='Research sections').get_by_role('link', name='Patent applications').click()
            assert page.url.endswith('#patents')
            page.locator('.original-title summary').first.click()
            assert page.get_by_text('一种基于不确定性感知协作图的群体脑机接口目标检测方法及系统', exact=True).is_visible()
            page.screenshot(path=str(shots / f'research-desktop{suffix}.png'), full_page=True)
            results['checks'].append('Research lists, patent anchor navigation and expandable Chinese source titles')
            page.get_by_role('navigation').get_by_role('link', name='Projects', exact=True).click()
            page.wait_for_selector('.project-card')
            assert page.locator('.project-card').count() == 4
            for project in json.loads((ROOT / 'data/projects.json').read_text()):
                visit('/projects/' + project['slug'] + '/')
                assert page.locator('h1').inner_text().startswith(project['name'])
                clean_copy()
                assert page.get_by_role('heading', name='Overview', exact=True).is_visible()
                assert page.get_by_role('heading', name='Architecture', exact=True).count() == 1
                fits(project['name'])
            visit('/cv/')
            clean_copy()
            research_records(full=False)
            honors_records()
            assert page.locator('.cv-section > h2').all_text_contents() == ['Education', 'Research Interests', 'Selected Publications', 'Honors & Awards', 'Selected Projects', 'Skills']
            assert page.locator('.education-entry').count() == 3
            assert page.locator('.cv-project').count() == 4
            assert page.get_by_role('link', name='Download CV (PDF)').count() == 0
            assert page.get_by_role('heading', name='Academic Service', exact=True).count() == 0
            page.get_by_role('button', name='Switch to light mode').click()
            page.screenshot(path=str(shots / f'cv-desktop{suffix}.png'), full_page=True)
            page.get_by_role('button', name='Switch to dark mode').click()
            results['checks'].append('Structured CV with selected work, honors, confirmed education, skills and hidden empty fields')
            visit('/404.html')
            assert page.get_by_role('link', name='Back to home').is_visible()
            page.set_viewport_size({'width': 390, 'height': 844})
            visit('/')
            page.get_by_role('button', name='Switch to light mode').click()
            fits('Mobile homepage 390px')
            page.screenshot(path=str(shots / f'home-mobile{suffix}.png'), full_page=True)
            for path in ('/research/', '/projects/', '/cv/', '/projects/driveguard-rt/'):
                visit(path)
                fits('Mobile ' + path)
                if path == '/cv/':
                    clean_copy()
                    page.screenshot(path=str(shots / f'cv-mobile{suffix}.png'), full_page=True)
                if path == '/research/':
                    research_records()
                    page.locator('.original-title summary').nth(1).click()
                    fits('Mobile expanded Chinese patent title')
                    page.screenshot(path=str(shots / f'research-mobile{suffix}.png'), full_page=True)
            page.set_viewport_size({'width': 320, 'height': 740})
            visit('/')
            fits('Small mobile homepage 320px')
            visit('/research/')
            fits('Small mobile research 320px')
            visit('/cv/')
            fits('Small mobile CV 320px')
            page.set_viewport_size({'width': 820, 'height': 1180})
            for path in ('/', '/research/', '/projects/', '/cv/'):
                visit(path)
                fits('Tablet ' + path)
            visit('/')
            page.screenshot(path=str(shots / f'home-tablet{suffix}.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 1000})
            visit('/')
            page.get_by_role('navigation', name='Main navigation').get_by_role('link', name='Blog').click()
            page.wait_for_url('**/blog/')
            page.wait_for_timeout(1000)
            assert '秘密基地' in page.title()
            fits('Desktop preserved blog')
            featured_slider_works('Desktop')
            assert page.locator('#swiper_container').evaluate('(e) => e.swiper.params.effect') == 'fade'
            assert page.evaluate("GLOBAL_CONFIG.root") == prefix + '/blog/'
            assert page.locator('.webinfo-item').filter(has_text='文章数目').locator('.item-count').inner_text() == str(len(posts))
            covers = page.locator('.recent-post-item .post_cover img')
            assert covers.count() == 10
            assert covers.evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 10 && getComputedStyle(i).objectFit === "contain")')
            page.screenshot(path=str(shots / f'blog-desktop{suffix}.png'), full_page=True, animations='disabled')
            bullets = page.locator('.blog-slider__pagination .swiper-pagination-bullet')
            assert bullets.count() >= 2
            active_title = page.locator('.blog-slider__item.swiper-slide-active .blog-slider__title').inner_text()
            next_index = (page.locator('#swiper_container').evaluate('(e) => e.swiper.realIndex') + 1) % bullets.count()
            bullets.nth(next_index).click()
            assert page.locator('.blog-slider__item.swiper-slide-active .blog-slider__title').inner_text() != active_title
            page.locator('.blog-slider__item.swiper-slide-active .blog-slider__title').click()
            page.wait_for_url('**/blog/2022/**')
            results['checks'].append('Featured article dots and article link')
            visit('/blog/')
            page.locator('#menus a[href="' + prefix + '/blog/playground/"]').first.click()
            page.wait_for_url('**/blog/playground/')
            assert page.get_by_role('heading', name='奇妙小玩意.').is_visible()
            page.get_by_role('link', name='进入体验').click()
            page.wait_for_url('**/blog/air-conditioner/')
            page.get_by_role('button', name='开关空调').wait_for()
            page.get_by_role('button', name='开关空调').click()
            page.get_by_role('button', name='升高温度').click()
            assert '27°C' in page.locator('#air-conditioner-vue').inner_text()
            page.get_by_role('button', name='制热').click()
            assert '☀️' in page.locator('#air-conditioner-vue').inner_text()
            page.get_by_role('button', name='制冷').click()
            page.get_by_role('button', name='降低温度').click()
            assert '26°C' in page.locator('#air-conditioner-vue').inner_text()
            page.get_by_role('link', name='返回奇妙小玩意').click()
            page.wait_for_url('**/blog/playground/')
            results['checks'].append('Blog to Playground navigation and air-conditioner controls')
            visit('/blog/')
            # Exercise real legacy PJAX navigation, not only direct URL requests.
            article_url = prefix + '/blog/' + posts[0]['path']
            page.locator('a.article-title').filter(has_text=posts[0]['title']).click()
            page.wait_for_selector('#article-container')
            page.wait_for_timeout(1100)  # Allow the retained theme's entrance animation to finish.
            assert '/blog/2026/' in urllib.parse.unquote(page.url)
            assert page.locator('.post-title').inner_text() == 'Docker 入门实战笔记'
            assert page.locator('#article-container img').count() == 6
            assert page.locator('time.post-meta-date-updated').count() == 0
            assert page.locator('.examples-download').count() == 1
            assert page.get_by_role('link', name='技术爬爬虾《40分钟的Docker实战攻略》', exact=True).get_attribute('href') == 'https://www.bilibili.com/video/BV1THKyzBER6/'
            assert page.locator('#article-container').inner_text().strip()
            assert page.locator('.highlight').count() > 0
            assert page.locator('#card-toc').count() > 0
            assert page.locator('.post-title').is_visible()
            page.screenshot(path=str(shots / f'article-desktop{suffix}.png'))
            page.locator('#article-container').scroll_into_view_if_needed()
            page.screenshot(path=str(shots / f'article-content{suffix}.png'))
            results['checks'].append('Blog PJAX article navigation, TOC and highlighted code')
            visit('/blog/about/')
            page.wait_for_timeout(1100)
            assert page.locator('.about-hero-avatar').evaluate('(i) => i.complete && i.naturalWidth === 1122')
            assert page.locator('.ba-personality h2').inner_text() == 'INFJ · 提倡者'
            assert page.locator('.ba-infj').evaluate('(i) => i.complete && i.naturalWidth > 0')
            assert page.locator('.ba-tech').count() == 8
            assert page.locator('.ba-timeline li').count() == 3
            assert page.locator('.ba-gallery').count() == 0
            assert page.locator('.ba-philosophy').inner_text().count('Stay curious.') == 1
            fits('Desktop personalized blog About')
            for y in range(0, int(page.evaluate('document.body.scrollHeight')), 600):
                page.evaluate('y => scrollTo(0,y)', y)
                page.wait_for_timeout(100)
            page.wait_for_timeout(250)
            badge = page.locator('#ghbdages img[alt="本站已在苏进行备案"]')
            assert badge.evaluate('(i) => i.complete && i.naturalWidth === 149 && i.naturalHeight === 20')
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=str(shots / f'blog-about-desktop{suffix}.png'), full_page=True, animations='disabled')
            results['checks'].append('Blog avatar, INFJ illustration, motto, removed cards and ICP SVG badge')
            for path in ('/blog/categories/Docker/', '/blog/tags/Docker/', '/blog/archives/2026/11/'):
                visit(path)
                assert page.locator('.article-sort-item-title').all_text_contents() == ['Docker 入门实战笔记']
                assert page.locator('time.post-meta-date-updated').count() == 0
            visit('/blog/categories/')
            assert page.locator('a[href*="/blog/categories/"]').count() > 0
            visit('/blog/tags/')
            assert page.locator('a[href*="/blog/tags/"]').count() > 0
            visit('/blog/link/')
            assert '友' in page.locator('body').inner_text()
            visit('/blog/archives/')
            assert page.locator('a[href*="/blog/2022/"]').count() > 0
            # A legacy URL must preserve query and fragment while moving to /blog/.
            visit('/' + urllib.parse.quote(posts[1]['path'], safe='/') + '?source=legacy#article-container')
            page.wait_for_selector('#article-container')
            assert '/blog/' in page.url and '?source=legacy' in page.url and '#article-container' in page.url
            results['checks'].append('Historical redirect preserves query and fragment')
            page.set_viewport_size({'width': 390, 'height': 844})
            visit('/blog/')
            fits('Mobile preserved blog')
            featured_slider_works('Mobile')
            page.wait_for_timeout(1000)
            page.screenshot(path=str(shots / f'blog-mobile{suffix}.png'), animations='disabled')
            page.evaluate('document.body.scrollTop = 780')
            assert page.evaluate('document.body.scrollTop > 0')
            assert page.locator('.recent-post-item').first.evaluate('(e) => {const r=e.getBoundingClientRect();return r.bottom>60 && r.top<innerHeight}')
            page.screenshot(path=str(shots / f'blog-mobile-articles{suffix}.png'), animations='disabled')
            page.set_viewport_size({'width': 820, 'height': 1180})
            for path in ('/blog/', '/blog/about/', '/blog/playground/', '/blog/air-conditioner/'):
                visit(path)
                fits('Tablet ' + path)
            visit('/blog/')
            featured_slider_works('Tablet')
            page.screenshot(path=str(shots / f'blog-tablet{suffix}.png'), full_page=True, animations='disabled')
            page.set_viewport_size({'width': 390, 'height': 844})
            visit('/blog/about/')
            page.wait_for_timeout(1100)
            fits('Mobile personalized blog About')
            page.locator('.ba-personality').scroll_into_view_if_needed()
            image_bounds = page.locator('.ba-infj').bounding_box()
            card_bounds = page.locator('.ba-personality').bounding_box()
            assert image_bounds['y'] >= card_bounds['y'] and image_bounds['y'] + image_bounds['height'] <= card_bounds['y'] + card_bounds['height'], 'Mobile INFJ image is clipped'
            page.screenshot(path=str(shots / f'blog-personality-mobile{suffix}.png'), animations='disabled')
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=str(shots / f'blog-about-mobile{suffix}.png'), full_page=True, animations='disabled')
            visit('/blog/' + urllib.parse.quote(posts[0]['path'], safe='/'))
            fits('Mobile Docker note')
            assert page.locator('#article-container img').count() == 6
            page.screenshot(path=str(shots / f'docker-mobile{suffix}.png'), animations='disabled')
            visit('/blog/' + urllib.parse.quote(posts[-1]['path'], safe='/'))
            fits('Mobile preserved article')
            page.locator('.academic-home-link').click()
            page.wait_for_selector('h1')
            assert page.locator('h1').inner_text().startswith('Hao Liu')
            results['checks'].append('Return from legacy blog to academic home')
            # Local raster images and embedded article images must decode successfully.
            visit('/blog/' + urllib.parse.quote(posts[0]['path'], safe='/'))
            broken = page.evaluate("""() => [...document.querySelectorAll('img')].filter(i => i.complete && !i.naturalWidth && (i.currentSrc.startsWith(location.origin) || i.currentSrc.startsWith('data:'))).map(i => i.currentSrc.slice(0,180))""")
            assert not broken, f'Broken local or embedded images: {broken}'
            image_paths = ['/' + p.relative_to(out).as_posix() for p in (out / 'blog').rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico')]
            # Chromium's request interception can reject ICO image loads; decode local assets without interception.
            asset_context = browser.new_context()
            asset_page = asset_context.new_page()
            asset_page.goto(start + '/', wait_until='load')
            decoded = asset_page.evaluate("""async paths => {
              const failures = [];
              for (let i = 0; i < paths.length; i += 8) {
                await Promise.all(paths.slice(i, i + 8).map(src => new Promise(resolve => {
                  const image = new Image();
                  const timer = setTimeout(() => { failures.push(src + ' (timeout)'); resolve(); }, 20000);
                  image.onload = () => { clearTimeout(timer); resolve(); };
                  image.onerror = () => { clearTimeout(timer); failures.push(src); resolve(); };
                  image.src = src;
                })));
              }
              return failures;
            }""", [prefix + value for value in image_paths])
            asset_context.close()
            assert not decoded, f'Undecodable preserved images: {decoded}'
            results['local_images_decoded'] = len(image_paths)
            browser.close()
        assert not results['page_errors'], results['page_errors']
        assert not results['local_http_errors'], results['local_http_errors']
        results['passed'] = True
    finally:
        server.shutdown()
        report_suffix = '-production' if report['production'] else ('-preview' if prefix else '')
        (ROOT / 'reports' / ('browser' + report_suffix + '.json')).write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
