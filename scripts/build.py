#!/usr/bin/env python3
"""Build the academic homepage and preserved Hexo blog into one Pages artifact."""
import argparse
import datetime
import hashlib
import html
import json
import re
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
import markdown
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from blog import finish_blog, personalize, render_new_posts

ROOT = Path(__file__).resolve().parents[1]
OLD_HOSTS = {'www.billysturate.top', 'billysturate.top', 'billysturate.github.io', 'billy-sturate-github-io.vercel.app'}

def read_json(path):
    return json.loads((ROOT / path).read_text())

def md(path):
    return markdown.markdown(path.read_text(), extensions=['extra', 'sane_lists'])

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-path', default='')
    parser.add_argument('--site-url', default='http://localhost:8000')
    parser.add_argument('--output', default='dist')
    parser.add_argument('--production', action='store_true')
    args = parser.parse_args()
    base = '/' + args.base_path.strip('/') if args.base_path.strip('/') else ''
    if not re.fullmatch(r'(?:/[a-zA-Z0-9_-]+)*', base):
        parser.error('base-path must contain simple URL segments')
    origin = args.site_url.rstrip('/')
    if urllib.parse.urlsplit(origin).scheme not in ('http', 'https'):
        parser.error('site-url must be an http(s) origin')
    out = (ROOT / args.output).resolve()
    # Never allow --output to remove source or backup directories.
    if out.parent != ROOT or out.name not in ('dist', 'dist-preview', 'dist-production'):
        parser.error('output must be dist, dist-preview, or dist-production in this project')
    if args.production and (base or origin != 'https://www.billysturate.top'):
        parser.error('production requires the confirmed canonical domain and an empty base path')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    site = ROOT / 'legacy/site'
    if not (site / 'index.html').is_file():
        raise SystemExit('Missing preserved blog. Restore legacy/site from the original backup.')
    asset_manifest = read_json('legacy/assets.json')
    profile = read_json('data/profile.json')
    blog_config = read_json('data/blog.json')
    new_pages = render_new_posts()
    new_article_count = len(new_pages)
    from playground import new_playground_page
    new_pages.update(new_playground_page())
    total_posts = sum(bool(re.match(r'^20\d\d/', p.relative_to(site).as_posix())) for p in site.rglob('*.html')) + new_article_count
    asset_map = {}
    for url, item in asset_manifest.items():
        if 'local' in item:
            asset_map[url] = base + '/blog/' + item['local']
        elif 'file' in item:
            asset_map[url] = base + '/blog/vendor/' + Path(item['file']).name
        elif 'reference' in item:
            asset_map[url] = item['reference']
    # Deliberate replacements for dead brand icons, not article illustrations.
    for old, new in {
        'https://bu.dusays.com/2023/01/26/63d157fc636f6.jpg': blog_config['avatar'],
        'https://bu.dusays.com/2023/08/01/64c8ca65ac6d3.jpg': '/assets/blog/icons/cplusplus.svg',
        'https://bu.dusays.com/2024/01/06/659900e3a27b6.png': '/assets/blog/icons/rust.svg',
        'https://bu.dusays.com/2024/01/06/6598fe4d06ef4.png': '/assets/blog/icons/git.svg',
    }.items():
        asset_map[old] = base + new
    for old, new in blog_config.get('cover_replacements', {}).items():
        asset_map[old] = asset_map.get(new, new)

    def url_rewrite(value):
        if not value or value.startswith(('data:', '#', 'mailto:', 'tel:', 'javascript:')):
            return value
        if value.startswith(base + '/assets/'):
            return value
        # Vendors are mapped before origin/path processing.
        absolute = 'https:' + value if value.startswith('//') else value
        if absolute in asset_map:
            return asset_map[absolute]
        parts = urllib.parse.urlsplit(value)
        if parts.hostname and parts.hostname.lower() in OLD_HOSTS:
            path = parts.path or '/'
            if base and path.startswith(base + '/'):
                path = path[len(base):]
            if path == '/blog' or path.startswith('/blog/'):
                path = path[5:] or '/'
            return base + '/blog' + (path if path.startswith('/') else '/' + path) + ('?' + parts.query if parts.query else '') + ('#' + parts.fragment if parts.fragment else '')
        if value.startswith('/') and not value.startswith('//'):
            if base and value.startswith(base + '/'):
                return value
            if value == '/blog' or value.startswith('/blog/'):
                return base + value
            return base + '/blog' + value
        return value

    def rewrite_text(text):
        # Exact known remote dependencies, including URLs in inline theme config.
        for old, new in sorted(asset_map.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(old, new)
            text = text.replace(old.replace('https:', '', 1), new)
        text = re.sub(r'https?://(?:www\.)?billysturate\.top(?=[/\"\'\s<]|$)', lambda _: origin + base + '/blog', text, flags=re.I)
        # Quoted paths in HTML attributes, inline configuration, JavaScript and JSON.
        text = re.sub(r'([\"\'`])(/(?!/)[^\"\'`\s<>]*)(\1)', lambda m: m[1] + url_rewrite(m[2]) + m[3], text)
        text = re.sub(r'url\(\s*([\"\']?)(/(?!/)[^\"\')]+)\1\s*\)', lambda m: 'url(' + m[1] + url_rewrite(m[2]) + m[1] + ')', text)
        text = text.replace('window.location.origin;', 'window.location.origin + ' + json.dumps(base + '/blog/') + ';')
        return text

    posts = []
    html_pages = []
    redirects = []
    missing_images = []
    unchanged = 0
    for source in sorted([p for p in site.rglob('*') if p.is_file()] + [site / name for name in new_pages]):
        rel = source.relative_to(site)
        is_new = rel.as_posix() in new_pages
        dest = out / 'blog' / rel
        if source.suffix.lower() not in ('.html', '.css', '.js', '.json', '.xml', '.txt', '.webmanifest'):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        else:
            text = new_pages[rel.as_posix()] if is_new else source.read_text(encoding='utf-8')
            if source.suffix == '.html':
                original = BeautifulSoup(text, 'html.parser')
                article = original.select_one('#article-container')
                if article is not None and re.match(r'^20\d\d/', rel.as_posix()):
                    title_el = original.select_one('h1.post-title') or original.select_one('h1')
                    date_el = original.select_one('time[datetime]')
                    posts.append({'title': title_el.get_text(' ', strip=True) if title_el else original.title.get_text().split(' | ')[0], 'date': date_el['datetime'][:10] if date_el else '/'.join(rel.parts[:3]).replace('/', '-'), 'path': rel.parent.as_posix() + '/', 'text': article.get_text(' ', strip=True)})
                migrated = BeautifulSoup(rewrite_text(text), 'html.parser')
                for tag in migrated.find_all(True):
                    for attr in ('href', 'src', 'data-src', 'data-lazy-src', 'data-background', 'poster', 'action', 'content'):
                        if isinstance(tag.get(attr), str):
                            tag[attr] = url_rewrite(tag[attr])
                    if tag.has_attr('srcset'):
                        tag['srcset'] = ', '.join(url_rewrite(part.strip().split()[0]) + (' ' + ' '.join(part.strip().split()[1:]) if len(part.strip().split()) > 1 else '') for part in tag['srcset'].split(',') if part.strip())
                personalize(migrated, base, blog_config, total_posts)
                article_missing = []
                for image in migrated.select('img'):
                    image_url = image.get('data-lazy-src') or image.get('data-src') or image.get('src')
                    if asset_manifest.get(image_url, {}).get('status') == 'unavailable':
                        image['data-original-src'] = image_url
                        image['src'] = base + '/blog/missing-image.svg'
                        for attr in ('data-src', 'data-lazy-src'):
                            if image.has_attr(attr):
                                image[attr] = base + '/blog/missing-image.svg'
                        image['class'] = image.get('class', []) + ['legacy-missing-image']
                        image['alt'] = '原截图暂缺' + ('：' + image['alt'] if image.get('alt') else '')
                        in_article = image.find_parent(id='article-container') is not None
                        missing_images.append({'page': rel.as_posix(), 'url': image_url, 'in_article': in_article})
                        if in_article:
                            article_missing.append(image_url)
                if migrated.head:
                    icon = migrated.find('link', rel=lambda value: value and 'icon' in value)
                    if icon and asset_manifest.get(icon.get('href'), {}).get('status') == 'unavailable':
                        icon['href'] = base + '/blog/img/favicon.png'
                    compat = migrated.new_tag('link', rel='stylesheet', href=base + '/assets/legacy-compat.css')
                    migrated.head.append(compat)
                if article_missing:
                    notice = migrated.new_tag('aside')
                    notice['class'] = 'legacy-image-notice'
                    notice.string = f'原图床的 {len(article_missing)} 张截图暂时无法访问，现有正文与代码完整保留。'
                    migrated.select_one('#article-container').insert_before(notice)
                # Keep navigation back to the academic homepage outside the legacy PJAX surface.
                back = migrated.new_tag('a', href=base + '/', target='_self')
                back['class'] = 'academic-home-link'
                back['style'] = 'position:fixed;bottom:18px;left:18px;z-index:9999;padding:7px 12px;border-radius:7px;background:#fff;color:#24372b;border:1px solid #cdd6cd;font:12px/1.6 sans-serif;box-shadow:0 2px 8px #0001'
                back.string = '← ' + profile['name'] + ' · Home'
                if migrated.body:
                    migrated.body.append(back)
                # Limit legacy PJAX to the blog, including on the academic-home link.
                for script in migrated.select('script:not([src])'):
                    if script.string and "elements: 'a:not([target=" in script.string:
                        script.string = script.string.replace("elements: 'a:not([target=\"_blank\"])'", "elements: 'a[href^=\"" + base + "/blog/\"]:not([target])'")
                canonical = migrated.find('link', rel='canonical')
                page_path = rel.parent.as_posix() + '/' if rel.name == 'index.html' else rel.as_posix()
                if page_path == './':
                    page_path = ''
                if canonical:
                    canonical['href'] = origin + base + '/blog/' + page_path
                if rel.as_posix() == 'playground/index.html':
                    for meta in migrated.select('meta[property="og:url"]'):
                        meta['content'] = origin + base + '/blog/' + page_path
                after_article = migrated.select_one('#article-container')
                # A URL printed as text can legitimately change; all other article text must survive.
                def normalized(el):
                    t = el.get_text(' ', strip=True)
                    return re.sub(r'https?://[^\s]+', '[URL]', t)
                if not is_new and article is not None and re.match(r'^20\d\d/', rel.as_posix()):
                    if after_article is None or normalized(article) != normalized(after_article):
                        raise ValueError(f'Article text changed during migration: {rel}')
                    unchanged += 1
                write(dest, str(migrated))
                html_pages.append('blog/' + page_path)
                if not is_new and rel.as_posix() not in ('index.html', '404.html'):
                    target = base + '/blog/' + page_path
                    encoded = html.escape(target, quote=True)
                    write(out / rel, '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta name="robots" content="noindex"><link rel="canonical" href="' + html.escape(origin + target, quote=True) + '"><title>Page moved</title></head><body><p>This page has moved to <a href="' + encoded + '">the preserved blog</a>.</p><script>location.replace(' + json.dumps(target) + ' + location.search + location.hash)</script></body></html>')
                    redirects.append({'from': '/' + page_path, 'to': '/blog/' + page_path})
            else:
                rewritten = rewrite_text(text)
                if rel.as_posix() == 'js/utils.js':
                    # Long percent-encoded Chinese article URLs exceed the archived QR
                    # widget's high-correction capacity; low correction still scans.
                    rewritten = rewritten.replace('correctLevel: QRCode.CorrectLevel.H', 'correctLevel: QRCode.CorrectLevel.L')
                write(dest, rewritten)
        # Preserve direct historical resource URLs too.
        if source.suffix != '.html' and rel.parts[0] not in ('assets',):
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, out / rel)

    # Rebase CSS-relative vendor dependencies to their snapshotted files.
    vendor = out / 'blog/vendor'
    vendor.mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'assets/missing-image.svg', out / 'blog/missing-image.svg')
    css_url = re.compile(r'url\(\s*[\"\']?([^\"\')]+)[\"\']?\s*\)')
    for original_url, item in asset_manifest.items():
        if 'file' not in item:
            continue
        source = ROOT / item['file']
        dest = vendor / source.name
        if source.suffix in ('.css', '.js'):
            text = source.read_text(errors='replace')
            if source.suffix == '.css':
                text = css_url.sub(lambda m: 'url(' + json.dumps(asset_map.get(urllib.parse.urljoin(original_url, m[1]), urllib.parse.urljoin(original_url, m[1])) if not m[1].startswith(('data:', '#')) else m[1]) + ')', text)
            write(dest, rewrite_text(text))
        else:
            shutil.copy2(source, dest)

    posts.sort(key=lambda p: (p['date'], p['path']), reverse=True)
    html_pages.extend(finish_blog(out, posts, base, origin))
    # Fully local search index for archived articles (also useful for future integrations).
    write(out / 'blog/search.json', json.dumps(posts, ensure_ascii=False))
    papers, projects, patents = read_json('data/publications.json'), read_json('data/projects.json'), read_json('data/patents.json')
    awards = read_json('data/awards.json')
    selected_papers = [paper for paper in papers if paper.get('selected')]
    for project in projects:
        project['article'] = next((p['path'] for p in posts if project['article_match'] and project['article_match'].lower() in (p['path'] + p['title']).lower()), None)
    shutil.copytree(ROOT / 'assets', out / 'assets')
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape(), undefined=StrictUndefined)
    structured = {'@context': 'https://schema.org', '@type': 'Person', 'name': profile['name'], 'alternateName': profile['chinese_name'], 'url': origin + base + '/', 'sameAs': [profile['github']], 'knowsAbout': profile['interests']}
    shared = {'profile': profile, 'papers': papers, 'selected_papers': selected_papers, 'patents': patents, 'awards': awards, 'projects': projects, 'base': base, 'origin': origin, 'year': datetime.date.today().year, 'structured': structured, 'description': None, 'style_version': hashlib.sha256((ROOT / 'assets/site.css').read_bytes()).hexdigest()[:12]}

    def render(template, path, **context):
        write(out / path, env.get_template(template).render(**(shared | {'canonical': origin + base + '/' + (path.removesuffix('index.html')), 'active': ''} | context)))
        if path != '404.html':
            html_pages.append(path.removesuffix('index.html'))

    render('index.html', 'index.html', title=profile['name'], active='about', about=md(ROOT / 'content/about.md'), post_count=len(posts), latest_posts=posts[:3])
    render('list.html', 'research/index.html', title='Research', active='research', eyebrow='Publications & Patent Applications', intro='Trustworthy learning, multimodal reasoning, and human–machine intelligence.')
    render('list.html', 'projects/index.html', title='Projects', active='projects', eyebrow='Selected Engineering Work', intro='Robot coordination, perception scheduling, event-driven networking, and observable AI systems.')
    for project in projects:
        render('project.html', f'projects/{project["slug"]}/index.html', title=project['name'], active='projects', project=project, body=md(ROOT / 'content/projects' / project['body']))
    render('cv.html', 'cv/index.html', title='CV', active='cv', body=md(ROOT / 'content/cv.md'))
    render('404.html', '404.html', title='Page not found')
    write(out / '.nojekyll', '')
    write(out / 'robots.txt', 'User-agent: *\nAllow: /\nSitemap: ' + origin + base + '/sitemap.xml\n')
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    sitemap = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for path in sorted(set(html_pages) - {'blog/404.html'}):
        node = ET.SubElement(sitemap, 'url')
        ET.SubElement(node, 'loc').text = origin + base + '/' + urllib.parse.quote(path, safe='/')
    write(out / 'sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sitemap, encoding='unicode'))
    feed = ET.Element('rss', version='2.0')
    channel = ET.SubElement(feed, 'channel')
    for name, value in [('title', 'BillySturate の秘密基地'), ('link', origin + base + '/blog/'), ('description', 'Preserved technical notes by BillySturate')]:
        ET.SubElement(channel, name).text = value
    for post in posts:
        item = ET.SubElement(channel, 'item')
        for name, value in [('title', post['title']), ('link', origin + base + '/blog/' + urllib.parse.quote(post['path'], safe='/')), ('guid', origin + base + '/blog/' + urllib.parse.quote(post['path'], safe='/')), ('description', post['text'][:500])]:
            ET.SubElement(item, name).text = value
    write(out / 'blog/feed.xml', '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(feed, encoding='unicode'))
    report = {'legacy_files': sum(p.is_file() for p in site.rglob('*')), 'legacy_html_pages': len(list(site.rglob('*.html'))), 'articles': len(posts), 'new_articles': new_article_count, 'article_text_verified': unchanged, 'redirects': len(redirects), 'base_path': base, 'site_url': origin, 'production': args.production, 'external_assets_saved': sum('file' in v or 'local' in v for v in asset_manifest.values()), 'external_assets_unavailable': [u for u,v in asset_manifest.items() if v['status'] == 'unavailable'], 'legacy_sha': 'd471274c1dc8d0370ca878b12dfe09a4cb161617'}
    report['direct_csdn_images'] = sum('reference' in v for v in asset_manifest.values())
    report['missing_article_images'] = len({item['url'] for item in missing_images if item['in_article']})
    write(out / 'migration-report.json', json.dumps(report, ensure_ascii=False, indent=2))
    write(ROOT / 'reports/redirects.json', json.dumps(redirects, ensure_ascii=False, indent=2))
    write(ROOT / 'reports/missing-images.json', json.dumps(missing_images, ensure_ascii=False, indent=2))
    report_suffix = '-production' if args.production else ('-preview' if base else '')
    write(ROOT / f'reports/build{report_suffix}.json', json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'external_assets_unavailable'}, ensure_ascii=False, indent=2))
    print(f'Built {out}; missing article images: {report["missing_article_images"]}; historical unavailable manifest entries: {len(report["external_assets_unavailable"])}')

if __name__ == '__main__':
    main()
