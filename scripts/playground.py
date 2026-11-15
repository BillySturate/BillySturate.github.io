"""Playground composition and shared blog navigation; original widget stays intact."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]

def new_playground_page():
    soup = BeautifulSoup((ROOT / 'legacy/site/air-conditioner/index.html').read_text(), 'html.parser')
    page = soup.select_one('#page')
    page.clear()
    page.append(soup.new_tag('div', id='playground-placeholder'))
    soup.title.string = '奇妙小玩意 | BillySturate の秘密基地'
    for meta in soup.select('meta[property="og:title"]'):
        meta['content'] = '奇妙小玩意'
    for meta in soup.select('meta[name="description"],meta[property="og:description"]'):
        meta['content'] = '一些不一定有用，但做起来很有意思的东西。'
    return {'playground/index.html': str(soup).replace('便携小空调 - 为你的夏日带去清凉!', '奇妙小玩意')}

def enhance_blog(soup, base):
    # Desktop and the existing mobile drawer have separate copies of this menu.
    for menu in soup.select('.menus_items'):
        for item in menu.select(':scope > .menus_item'):
            a = item.find('a', recursive=False)
            if a and a.get_text(strip=True) == '我的':
                a.clear()
                span = soup.new_tag('span'); span.string = '小玩意'; a.append(span)
                a['href'] = base + '/blog/playground/'
                for child in item.select('.menus_item_child'): child.decompose()
        if not menu.select_one('.blog-academic-nav'):
            item = soup.new_tag('div', attrs={'class':'menus_item blog-academic-nav'})
            a = soup.new_tag('a', href=base + '/', target='_self', attrs={'class':'site-page', 'aria-label':'个人主页 ↗'})
            a.append(BeautifulSoup('<svg class="blog-home-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-8 9 8M6 9v12h12V9M10 21v-7h4v7"/></svg><span>个人主页 <span aria-hidden="true">↗</span></span>', 'html.parser'))
            item.append(a); menu.append(item)
    if soup.head:
        soup.head.append(soup.new_tag('link', rel='stylesheet', href=base + '/assets/blog-nav.css'))
    toggle = soup.select_one('#toggle-menu a')
    if toggle:
        toggle['aria-label'] = '打开博客导航'
        toggle['title'] = '打开博客导航'
    placeholder = soup.select_one('#playground-placeholder')
    if placeholder:
        items = json.loads((ROOT / 'data/playground.json').read_text())
        for item in items:
            if not item['path'].startswith('/blog/') or not (ROOT / item['icon'].lstrip('/')).is_file():
                raise ValueError('Playground entries require /blog/ paths and real local icons')
        env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape())
        placeholder.replace_with(BeautifulSoup(env.get_template('playground.html').render(items=items, base=base), 'html.parser'))
    mount = soup.select_one('#air-conditioner-vue')
    if mount:
        article = mount.parent
        for old in list(article.find_all('blockquote', recursive=False)): old.decompose()
        old_title = soup.select_one('#page > .page-title')
        if old_title: old_title.decompose()
        header = BeautifulSoup('<header class="ac-heading"><a class="pg-back" href="' + base + '/blog/playground/">← 返回奇妙小玩意</a><h1>便携小空调</h1><p>代码写热了？来吹吹空调。</p><small>Powered by JavaScript. Cooling effect not guaranteed.</small></header>', 'html.parser')
        article.insert(0, header)
        article['class'] = article.get('class', []) + ['playground-ac']
        article.insert(0, soup.new_tag('link', rel='stylesheet', href=base + '/assets/playground.css'))
        # Add accessible names to existing Vue controls without changing handlers.
        script = soup.new_tag('script', attrs={'data-pjax':''})
        script.string = '''(()=>{const root=document.querySelector('#air-conditioner-vue');if(!root)return;const label=()=>{root.querySelectorAll('audio').forEach(a=>{if(a.dataset.pgSafeAudio)return;a.dataset.pgSafeAudio='true';const play=a.play;a.play=function(){const result=play.call(this);return result&&result.catch(error=>{if(!['AbortError','NotAllowedError'].includes(error.name))throw error;});};});['制冷','开关空调','制热','升高温度','降低温度'].forEach((text,i)=>{const b=root.querySelectorAll('.air-conditioner-controller button')[i];if(b){b.setAttribute('aria-label',text);b.title=text;}});};const observer=new MutationObserver(label);observer.observe(root,{childList:true,subtree:true});label();document.addEventListener('pjax:send',()=>{observer.disconnect();const power=root.querySelector('.anzhiyu-button-danger');if(power)power.click();root.querySelectorAll('audio').forEach(a=>{a.pause();a.currentTime=0;});},{once:true});})();'''
        article.append(script)
