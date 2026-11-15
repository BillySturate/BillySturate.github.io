"""Blog identity, local-clock appearance, copyright and production statistics."""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def refine_blog_home(soup, base):
    data = json.loads((ROOT/'data/blog-home.json').read_text())
    banner = soup.select_one('#bannerGroup .banners-title')
    if banner:
        for el, text in zip(banner.select('.banners-title-big'), data['motto']): el.string = text
        banner.select_one('.banners-title-small').string = data['subtitle']
    for box in soup.select('.author-info__description'):
        box.clear()
        for text in data['description']:
            p = soup.new_tag('p'); p.string = text; box.append(p)
    # Remove only the two secondary groups from the blog index. The source
    # archive, featured carousel and lower article/category data remain intact.
    if soup.select_one('#home_top'):
        for card_group in soup.select('#home_top .categoryGroup,#home_top #topPostGroup'):
            card_group.decompose()
    for box in soup.select('#footer-wrap .copyright'):
        box.clear(); box.append('©2021 – ')
        year = soup.new_tag('span', attrs={'data-blog-year':''}); year.string = str(datetime.date.today().year)
        box.append(year); box.append(' By BillySturate')
    for script in list(soup.select('script[src]')):
        if 'busuanzi' in script['src']: script.decompose()
    for item in soup.select('.webinfo-item'):
        if item.select_one('#busuanzi_value_site_uv,#busuanzi_value_site_pv'):
            item['data-live-stat'] = ''; item['hidden'] = ''
    # Reuse the existing manual theme switch and its stored preference. Only the
    # automatic default changes from OS color-scheme to the visitor's local clock.
    for script in soup.select('script:not([src])'):
        if script.string and 'const t = saveToLocal.get(\'theme\')' in script.string:
            text = script.string
            start = text.index("const t = saveToLocal.get('theme')")
            end = text.index('const asideStatus', start)
            script.string = text[:start] + '''window.billyAutoTheme = function () {
              const t = saveToLocal.get('theme');
              if (t === 'light') activateLightMode();
              else if (t === 'dark') activateDarkMode();
              else { const hour = new Date().getHours();
                hour >= 7 && hour < 19 ? activateLightMode() : activateDarkMode(); }
            }; window.billyAutoTheme();
            ''' + text[end:]
    if soup.head:
        apple_icon = None
        for icon in soup.find_all('link', rel=lambda value: value and 'icon' in value):
            if any(rel.startswith('apple-touch-icon') for rel in icon.get('rel', [])):
                if apple_icon:
                    icon.decompose()
                else:
                    apple_icon = icon
                    icon['rel'] = 'apple-touch-icon'
                    icon['href'] = base + '/assets/apple-touch-icon.png'
                    icon['sizes'] = '180x180'
                continue
            icon['href'] = base + '/assets/favicon-64.png'
            icon['type'] = 'image/png'
        if not apple_icon:
            soup.head.append(soup.new_tag('link', rel='apple-touch-icon', href=base+'/assets/apple-touch-icon.png'))
        soup.head.append(soup.new_tag('link', rel='stylesheet', href=base+'/assets/blog-home.css'))
        soup.head.append(soup.new_tag('script', src=base+'/assets/blog-runtime.js', defer=''))
