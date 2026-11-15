#!/usr/bin/env python3
"""One-time, resumable snapshot of legacy dependencies; normal builds are offline."""
import concurrent.futures
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'legacy/site'
VENDOR = ROOT / 'legacy/vendor'
VENDOR.mkdir(exist_ok=True)
MANIFEST = ROOT / 'legacy/assets.json'
manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
urls = set()
CSS_URL = re.compile(r'url\(\s*[\"\']?([^\"\')]+)[\"\']?\s*\)')

def add(value, parent='https://www.billysturate.top/'):
    if not value or value.startswith(('data:', '#', 'javascript:')):
        return
    url = urllib.parse.urljoin(parent, value.strip())
    if urllib.parse.urlsplit(url).scheme in ('http', 'https'):
        urls.add(url)

for path in SITE.rglob('*.html'):
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    for el in soup.select('script[src],link[rel=stylesheet],img,source,video'):
        for attr in ('src', 'href', 'data-src', 'data-lazy-src', 'poster'):
            if el.get(attr, '').startswith(('https://', 'http://', '//')):
                add(el[attr])
    for el in soup.select('[style]'):
        for u in CSS_URL.findall(el['style']):
            if u.startswith(('https://', 'http://', '//')):
                add(u)
    for el in soup.select('script:not([src]),style'):
        for u in re.findall(r'https?://[^\s\"\'<>`\\]+', el.get_text()):
            if re.search(r'\.(?:css|js|png|jpg|jpeg|gif|webp|svg)(?:\?|$)', u):
                add(u)
for p in SITE.rglob('*.css'):
    for u in CSS_URL.findall(p.read_text()):
        if u.startswith(('https://', 'http://', '//')):
            add(u)

def fetch(url):
    previous = manifest.get(url, {})
    # Direct image references are intentional user-authored recovery records.
    # Re-running the optional snapshot must not overwrite them with old-host 404s.
    if previous.get('reference'):
        return url, previous
    if previous.get('file') and (ROOT / previous['file']).exists():
        return url, previous
    # Local copies of the theme's core scripts are already in the original repo.
    m = re.search(r'hexo-theme-anzhiyu@[^/]+/source/(js/[^?]+)', url)
    if m and (SITE / m[1]).is_file():
        return url, {'local': m[1], 'status': 'original-repository'}
    alternatives = [url]
    if 'qrcodejs/1.0.0/qrcode.min.js' in url:
        alternatives.insert(0, 'https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js')
    if 'npm.elemecdn.com/' in url:
        alternatives.insert(0, url.replace('https://npm.elemecdn.com/', 'https://cdn.jsdelivr.net/npm/'))
    errors = []
    for candidate in alternatives:
        try:
            candidate = urllib.parse.quote(candidate, safe=":/?#[]@!$&'()*+,;=%")
            req = urllib.request.Request(candidate, headers={'User-Agent': 'Mozilla/5.0 (legacy-site-preservation)'})
            with urllib.request.urlopen(req, timeout=12) as response:
                content_type = response.headers.get('Content-Type', '')
                body = response.read(20_000_001)
                if len(body) > 20_000_000:
                    raise ValueError('asset exceeds 20 MB')
                if 'text/html' in content_type:
                    raise ValueError('returned HTML instead of asset')
            suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
            if not re.fullmatch(r'\.[a-z0-9]{1,6}', suffix):
                suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif', 'image/svg+xml': '.svg', 'image/x-icon': '.ico', 'image/webp': '.webp', 'text/css': '.css', 'application/javascript': '.js'}.get(content_type.split(';')[0], '.bin')
            file = VENDOR / (hashlib.sha256(url.encode()).hexdigest()[:20] + suffix)
            file.write_bytes(body)
            return url, {'file': file.relative_to(ROOT).as_posix(), 'status': 'saved', 'fetched_from': candidate, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
        except Exception as e:
            errors.append(str(e))
    return url, {'status': 'unavailable', 'error': '; '.join(errors)}

seen = set()
for round_index in range(4):
    batch = sorted(urls - seen)
    if not batch:
        break
    print(f'Round {round_index + 1}: {len(batch)} assets', flush=True)
    seen.update(batch)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for i, (url, item) in enumerate(pool.map(fetch, batch), 1):
            manifest[url] = item
            if item.get('file', '').endswith('.css'):
                css = (ROOT / item['file']).read_text(errors='replace')
                for u in CSS_URL.findall(css):
                    add(u, url)
                for u in re.findall(r'@import\s+[\"\']([^\"\']+)', css):
                    add(u, url)
            if i % 25 == 0:
                print(f'  {i}/{len(batch)}', flush=True)
                MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'total': len(manifest), 'saved': sum('file' in v or 'local' in v for v in manifest.values()), 'unavailable': sum(v['status'] == 'unavailable' for v in manifest.values())}), flush=True)
