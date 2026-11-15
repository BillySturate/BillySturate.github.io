#!/usr/bin/env python3
"""Check every output page, local dependency, legacy redirect and archive checksum."""
import argparse
import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default='dist')
    args = parser.parse_args()
    out = ROOT / args.directory
    report = json.loads((out / 'migration-report.json').read_text())
    base = report['base_path']
    errors, checked, pages = [], set(), 0

    def check(value, page):
        if not value or value.startswith(('data:', 'javascript:', 'mailto:', 'tel:', '#')):
            return
        url = urllib.parse.urlsplit(value)
        if url.netloc or url.scheme:
            return
        origin_path = '/' + page.relative_to(out).as_posix()
        path = urllib.parse.unquote(urllib.parse.urlsplit(urllib.parse.urljoin('http://check' + base + origin_path, value)).path)
        if base:
            if not path.startswith(base + '/'):
                errors.append(f'Path escapes preview base: {value} in {page.relative_to(out)}')
                return
            path = path[len(base):]
        key = path
        if key in checked:
            return
        checked.add(key)
        target = out / path.lstrip('/')
        if not target.is_file() and not (target / 'index.html').is_file():
            errors.append(f'Missing: {value} in {page.relative_to(out)}')

    for page in out.rglob('*.html'):
        pages += 1
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        for tag in soup.select('[href],[src],[data-src],[data-lazy-src],[poster]'):
            for attr in ('href', 'src', 'data-src', 'data-lazy-src', 'poster'):
                if tag.get(attr):
                    check(tag[attr], page)
        for tag in soup.select('[style]'):
            for value in re.findall(r'url\([\"\']?([^\"\')]+)', tag['style']):
                check(value, page)
        if not soup.title or not soup.find('html'):
            errors.append(f'Incomplete HTML: {page}')
        if '/blog/blog/' in page.read_text() or (base and base + base + '/' in page.read_text()):
            errors.append(f'Duplicate path prefix: {page}')
    for css in out.rglob('*.css'):
        for value in re.findall(r'url\(\s*[\"\']?([^\"\')]+)', css.read_text()):
            check(value.strip(), css)
    for url, item in json.loads((ROOT / 'legacy/assets.json').read_text()).items():
        if 'file' in item:
            data = (ROOT / item['file']).read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                errors.append(f'Vendor checksum differs: {url}')
    manifest = json.loads((ROOT / 'legacy/manifest.json').read_text())
    for rel, digest in manifest['files'].items():
        if hashlib.sha256((ROOT / 'legacy/site' / rel).read_bytes()).hexdigest() != digest:
            errors.append(f'Original archive changed: {rel}')
    assert report['article_text_verified'] == 51
    assert report['articles'] == 51 + report['new_articles']
    assert report['legacy_html_pages'] == 139
    assert report['redirects'] == 137
    # Every post must remain discoverable exactly once across home pagination.
    posts = json.loads((out / 'blog/search.json').read_text())
    listed = []
    home_pages = [out / 'blog/index.html'] + list((out / 'blog/page').glob('*/index.html'))
    for file in home_pages:
        soup = BeautifulSoup(file.read_text(), 'html.parser')
        listed.extend(urllib.parse.unquote(a['href']).removeprefix(base + '/blog/') for a in soup.select('.recent-post-item .article-title'))
        assert not soup.select('time.post-meta-date-updated')
    assert len(listed) == len(set(listed)) == len(posts)
    assert set(listed) == {p['path'] for p in posts}
    for post in json.loads((ROOT / 'data/blog-posts.json').read_text()):
        soup = BeautifulSoup((out / 'blog' / post['path'] / 'index.html').read_text(), 'html.parser')
        ids = {el['id'] for el in soup.select('[id]')}
        for a in soup.select('#card-toc a[href^="#"],#article-container a[href^="#"]'):
            assert urllib.parse.unquote(a['href'][1:]) in ids, f'Broken Markdown heading link: {a["href"]}'
        assert soup.select_one('h1.post-title').get_text() == post['title']
        assert soup.select_one('.post-meta__box__tags')['href'] == base + '/blog/tags/' + post['tags'][0] + '/'
        if post.get('examples'):
            source = (ROOT / post['source']).parent
            with zipfile.ZipFile(out / 'blog/content' / source.name / 'examples.zip') as archive:
                assert archive.testzip() is None
                expected = {p.relative_to(source / post['examples']).as_posix(): p.read_bytes() for p in (source / post['examples']).rglob('*') if p.is_file()}
                assert set(archive.namelist()) == set(expected)
                for name, content in expected.items():
                    assert archive.read(name) == content
    for redirect in json.loads((ROOT / 'reports/redirects.json').read_text()):
        src = out / redirect['from'].lstrip('/')
        if src.is_dir():
            src /= 'index.html'
        text = src.read_text()
        if 'location.search + location.hash' not in text:
            errors.append(f'Redirect loses query or fragment: {src}')
    ET.parse(out / 'sitemap.xml')
    ET.parse(out / 'blog/feed.xml')
    assert (out / '.nojekyll').exists()
    assert not (out / 'CNAME').exists()
    result = {'pages_checked': pages, 'unique_local_paths_checked': len(checked), 'original_files_verified': len(manifest['files']), 'article_text_verified': report['article_text_verified'], 'total_posts_listed_once': len(listed), 'markdown_anchors_and_example_downloads': 'passed', 'errors': errors}
    report_suffix = '-production' if report['production'] else ('-preview' if base else '')
    (ROOT / 'reports' / ('validation' + report_suffix + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
