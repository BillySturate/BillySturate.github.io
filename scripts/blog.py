"""Small, data-driven additions to the preserved AnZhiYu static archive.

The historical source files remain immutable. All personalization and new
Markdown posts are composed into the same offline build artifact.
"""
import copy
import html
import json
import math
import re
import shutil
import urllib.parse
import zipfile
from pathlib import Path

import markdown
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / name).read_text())


def slug(value, separator='-'):
    return re.sub(r'[^\w\u4e00-\u9fff-]+', separator, value.lower()).strip(separator)


def fragment(text):
    return BeautifulSoup(text, 'html.parser')


def post_url(post, base=''):
    return base + '/blog/' + urllib.parse.quote(post['path'], safe='/')


def set_published_date(soup, date):
    """Change the displayed publication date without changing article URLs."""
    for el in soup.select('time.post-meta-date-created, .recent-post-item time, .article-sort-item time'):
        el['datetime'] = date + 'T00:00:00+08:00'
        el['title'] = '发表于 ' + date
        el.string = date
    for el in soup.select('meta[property="article:published_time"]'):
        el['content'] = date + 'T00:00:00+08:00'


def metadata(soup, title, description=None, image=None):
    soup.title.string = title + ' | BillySturateの秘密基地'
    for el in soup.select('meta[property="og:title"],meta[name="twitter:title"]'):
        el['content'] = title
    for el in soup.select('meta[name="description"],meta[property="og:description"],meta[name="twitter:description"]'):
        if description is not None:
            el['content'] = description
    for el in soup.select('meta[property="og:image"],meta[name="twitter:image"]'):
        if image:
            el['content'] = image


def image_source(image, url):
    image['src'] = url
    for attr in ('data-lazy-src', 'data-src', 'data-original-src', 'onerror'):
        image.attrs.pop(attr, None)
    image['loading'] = 'lazy'
    image['decoding'] = 'async'


def render_new_posts():
    """Use an original article shell, keeping the theme's navigation and JS."""
    shell = next((ROOT / 'legacy/site/2024').rglob('*.html')).read_text()
    pages = {}
    for post in load('data/blog-posts.json'):
        if not re.fullmatch(r'20\d\d/\d\d/\d\d/[^?#]+/', post['path']) or '..' in Path(post['path']).parts:
            raise ValueError('Invalid new blog post path: ' + post['path'])
        if (ROOT / 'legacy/site' / post['path'] / 'index.html').exists() or post['path'] + 'index.html' in pages:
            raise ValueError('A new post cannot replace an existing article: ' + post['path'])
        source = ROOT / post['source']
        directory = source.parent.name
        root = '/blog/content/' + directory + '/'
        text = source.read_text()
        # Obsidian heading links become ordinary anchors with matching TOC IDs.
        text = re.sub(r'\[\[#([^\]]+)\]\]', lambda m: '[' + m[1] + '](#' + slug(m[1]) + ')', text)
        text = re.sub(r'^# .+\n', '', text, count=1)
        body = fragment(markdown.markdown(text, extensions=['extra', 'toc', 'sane_lists'], extension_configs={'toc': {'slugify': slug}}))
        for el in body.select('img[src],a[href]'):
            attr = 'src' if el.name == 'img' else 'href'
            value = el[attr]
            if not urllib.parse.urlsplit(value).scheme and not value.startswith(('#', '/')):
                # Source notes can link to the original Chinese example directory.
                el[attr] = root + value.replace('实操示例/', 'examples/')
            if el.name == 'img':
                el['loading'] = 'lazy'
                el['decoding'] = 'async'
        for pre in list(body.select('pre')):
            code = pre.find('code')
            if code is None:
                continue
            lang = next((c.removeprefix('language-') for c in code.get('class', []) if c.startswith('language-')), 'text')
            try:
                lexer = get_lexer_by_name(lang)
            except ClassNotFound:
                lexer = TextLexer()
            code_text = code.get_text()
            colored = highlight(code_text, lexer, HtmlFormatter(nowrap=True))
            figure = fragment('<figure class="highlight ' + lang + '"><table><tbody><tr><td class="gutter"><pre></pre></td><td class="code"><pre></pre></td></tr></tbody></table></figure>').figure
            figure.select_one('.gutter pre').string = '\n'.join(str(i) for i in range(1, len(code_text.rstrip('\n').split('\n')) + 1))
            figure.select_one('.code pre').extend(fragment(colored).contents)
            pre.replace_with(figure)
        if post.get('examples'):
            body.append(fragment('<p><a class="examples-download" href="' + root + 'examples.zip" download>下载本文实操示例（Nginx / FastAPI / MongoDB）</a></p>'))
        soup = fragment(shell)
        cover = root + post['cover']
        metadata(soup, post['title'], post['description'], cover)
        for el in soup.select('.post-title,.post-copyright-title span,#nav #page-name'):
            el.string = post['title']
        for el in soup.select('time.post-meta-date-created,time.post-meta-date-updated'):
            el['datetime'] = post['date'] + 'T00:00:00+08:00'
            el['title'] = '发表于 ' + post['date']
            el.string = post['date']
        for el in soup.select('meta[property="article:published_time"],meta[property="article:modified_time"]'):
            el['content'] = post['date'] + 'T00:00:00+08:00'
        for el in soup.select('a.post-meta-categories'):
            el['href'] = '/categories/' + urllib.parse.quote(post['category'], safe='') + '/'
            el.string = post['category']
        tag_list = soup.select_one('.tag_share .post-meta__box__tag-list')
        tag_list.clear()
        for tag in post['tags']:
            a = soup.new_tag('a', href='/tags/' + urllib.parse.quote(tag, safe='') + '/', attrs={'class': 'post-meta__box__tags'})
            a.string = tag
            tag_list.append(a)
        for el in soup.select('[data-flag-title]'):
            el['data-flag-title'] = post['title']
        article = soup.select_one('#article-container')
        article.clear()
        article['class'] = article.get('class', []) + ['markdown-post']
        article.extend(list(body.contents))
        for el in soup.select('.relatedPosts,#pagination'):
            el.decompose()
        for el in soup.select('.post-copyright__original,.post-copyright__type a.link'):
            el['href'] = post_url(post)
            if el.select_one('span') is None and el.get_text(strip=True) != '原创':
                el.string = post_url(post)
        for el in soup.select('.post-meta-wordcount .word-count'):
            el.string = str(len(article.get_text()))
        wordcount = soup.select_one('.post-meta-wordcount')
        if wordcount:
            wordcount.clear()
            wordcount.string = '字数总计: ' + str(len(article.get_text()))
        readtime = soup.select_one('.post-meta-time')
        if readtime:
            readtime.clear()
            readtime.string = '阅读时长: ' + str(max(1, math.ceil(len(article.get_text()) / 500))) + ' 分钟'
        toc = soup.select_one('#card-toc .toc-content')
        if toc:
            toc.clear()
            ol = soup.new_tag('ol', attrs={'class': 'toc'})
            for heading in article.select('h2,h3'):
                li = soup.new_tag('li', attrs={'class': 'toc-item toc-level-' + heading.name[1]})
                a = soup.new_tag('a', href='#' + heading['id'], attrs={'class': 'toc-link'})
                span = soup.new_tag('span', attrs={'class': 'toc-text'})
                span.string = heading.get_text()
                a.append(span)
                li.append(a)
                ol.append(li)
            toc.append(ol)
        for script in soup.select('script:not([src])'):
            if script.string and 'GLOBAL_CONFIG_SITE' in script.string:
                script.string = re.sub(r"title: '[^']*'", lambda _: 'title: ' + json.dumps(post['title'], ensure_ascii=False), script.string)
                script.string = re.sub(r"postUpdate: '[^']*'", lambda _: 'postUpdate: ' + json.dumps(post['date']), script.string)
        pages[post['path'] + 'index.html'] = str(soup)
    return pages


def personalize(soup, base, config, count):
    """Presentation changes only; never edit historical article text."""
    # CSDN image hosts expect image requests without a third-party Referer,
    # including the separate <img> created by the retained lightbox plugin.
    if soup.head and not soup.find('meta', attrs={'name': 'referrer'}):
        soup.head.append(soup.new_tag('meta', attrs={'name': 'referrer', 'content': 'no-referrer'}))
    for image in soup.select('.avatar-img img,.author-img img,#loading-box img.loading-img'):
        image_source(image, base + config['avatar'])
    # Listing covers and small technology icons should survive PJAX without
    # waiting for the old theme's lazyload observer to be re-initialized.
    for image in soup.select('.post_cover img,.article-sort-item-img img,#home_top img,.tags-group-icon img'):
        url = image.get('data-lazy-src') or image.get('src')
        if url:
            image_source(image, url)
            image['loading'] = 'eager'
    # The large sidebar card originally hides its avatar in CSS; make the real
    # avatar available there as well without changing the card structure.
    for card in soup.select('.card-info-avatar'):
        if not card.select_one('img.blog-avatar'):
            image = soup.new_tag('img', src=base + config['avatar'], alt='BillySturate — penguin avatar', attrs={'class': 'blog-avatar', 'width': '72', 'height': '72'})
            card.insert(0, image)
    for a in soup.select('a.social-icon[title="Email"]'):
        a['href'] = 'mailto:billysturate@gmail.com'
    for image in soup.select('img'):
        if 'csdnimg.cn/' in (image.get('data-lazy-src') or image.get('src', '')):
            image['referrerpolicy'] = 'no-referrer'
    if not config['show_updated_dates']:
        for time in list(soup.select('time.post-meta-date-updated')):
            parent = time.parent
            # Everything after the publication <time> belongs to the updated
            # date cluster. Preserve other category/tag metadata siblings.
            published = parent.select_one('time.post-meta-date-created')
            if published:
                for following in list(published.next_siblings):
                    following.extract()
            else:
                time.decompose()
        for item in list(soup.select('.webinfo-item')):
            text = item.get_text()
            if '最后更新时间' in text:
                item.decompose()
            elif '文章数目' in text:
                value = item.select_one('.item-count,.webinfo-item-right')
                if value:
                    value.string = str(count)
        for script in soup.select('script:not([src])'):
            if script.string and 'noticeOutdate:' in script.string:
                script.string = re.sub(r'noticeOutdate: \{[^\n]*\},', 'noticeOutdate: undefined,', script.string)
    for value in soup.select('.site-data .length-num'):
        # The first entry is the article count, followed by tags/categories.
        if value.parent.select_one('.headline') and '文章' in value.parent.get_text():
            value.string = str(count)
    about = soup.select_one('#about-page')
    if about:
        from blog_about import render_about
        render_about(soup, base, config)
    from blog_home import refine_blog_home
    refine_blog_home(soup, base)
    from playground import enhance_blog
    enhance_blog(soup, base)
    # Small badges are eagerly loaded at their real size, independent of lazyload.
    for image in soup.select('#ghbdages img'):
        image_source(image, image.get('data-lazy-src') or image['src'])
        image['loading'] = 'eager'
        image['height'] = '20'


def finish_blog(out, posts, base, origin):
    """Integrate Markdown posts into all indexes using existing theme elements."""
    new = sorted(load('data/blog-posts.json'), key=lambda p: (p['date'], p['path']), reverse=True)
    if not new:
        return []
    blog = out / 'blog'
    # Publish only the self-contained note assets/examples; never depend on an
    # absolute path on the author's laptop in CI.
    for post in new:
        source = (ROOT / post['source']).parent
        dest = blog / 'content' / source.name
        shutil.copytree(source, dest, dirs_exist_ok=True)
        if post.get('examples'):
            with zipfile.ZipFile(dest / 'examples.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for file in sorted((source / post['examples']).rglob('*')):
                    if file.is_file():
                        archive.write(file, file.relative_to(source / post['examples']))
        post['cover_url'] = base + '/blog/content/' + source.name + '/' + post['cover']

    def read(path):
        return fragment((blog / path).read_text())

    def save(path, soup):
        file = blog / path
        file.parent.mkdir(parents=True, exist_ok=True)
        (file).write_text(str(soup))

    def path_of(a):
        return urllib.parse.unquote(urllib.parse.urlsplit(a['href']).path).removeprefix(base + '/blog/').strip('/') + '/'

    cards, entries = {}, {}
    home_files = ['index.html'] + [str(p.relative_to(blog)) for p in sorted((blog / 'page').glob('*/index.html'))]
    for file in home_files:
        soup = read(file)
        for el in soup.select('.recent-post-item'):
            cards[path_of(el.select_one('.article-title'))] = copy.deepcopy(el)
    for file in (blog / 'archives').rglob('*.html'):
        soup = fragment(file.read_text())
        for el in soup.select('.article-sort-item:not(.year)'):
            entries[path_of(el.select_one('.article-sort-item-title'))] = copy.deepcopy(el)
    for post in posts:
        if post['path'] in cards:
            set_published_date(cards[post['path']], post['date'])
        if post['path'] in entries:
            set_published_date(entries[post['path']], post['date'])
    card_shell, entry_shell = copy.deepcopy(next(iter(cards.values()))), copy.deepcopy(next(iter(entries.values())))
    for post in new:
        card, entry = copy.deepcopy(card_shell), copy.deepcopy(entry_shell)
        for node in (card, entry):
            for a in node.select('a'):
                a['href'] = post_url(post, base)
                a['title'] = post['title']
            for a in node.select('.article-title,.article-sort-item-title'):
                a.string = post['title']
            for image in node.select('img'):
                image_source(image, post['cover_url'])
                image['alt'] = post['title']
            for time in node.select('time'):
                time['datetime'] = post['date'] + 'T00:00:00+08:00'
                time['title'] = '发表于 ' + post['date']
                time.string = post['date']
            for tags in node.select('.article-meta.tags,.article-sort-item-tags'):
                tags.clear()
                for tag in post['tags']:
                    tags.append(fragment('<a class="article-meta__tags" href="' + base + '/blog/tags/' + urllib.parse.quote(tag, safe='') + '/"># ' + html.escape(tag) + '</a>'))
        category = card.select_one('.article-meta__categories')
        category['href'] = base + '/blog/categories/' + post['category'] + '/'
        category.string = post['category']
        card.select_one('.content').string = post['description']
        cards[post['path']], entries[post['path']] = card, entry
    assert len(cards) == len(entries) == len(posts), 'Every article must be present in the theme indexes'

    def set_canonical(soup, path):
        canonical = soup.select_one('link[rel="canonical"]')
        canonical['href'] = origin + base + '/blog/' + path
        for meta in soup.select('meta[property="og:url"]'):
            meta['content'] = canonical['href']

    def paginate(soup, index, count, root):
        nav = soup.select_one('#pagination')
        if count <= 1:
            if nav:
                nav.decompose()
            return
        if nav is None:
            nav = soup.new_tag('nav', id='pagination')
            (soup.select_one('#recent-posts') or soup.select_one('.article-sort').parent).append(nav)
        nav.clear()
        group = soup.new_tag('div', attrs={'class': 'pagination'})
        for number in range(count):
            if number == index:
                item = soup.new_tag('span', attrs={'class': 'page-number current', 'aria-current': 'page'})
            else:
                path = root + (f'page/{number + 1}/' if number else '')
                item = soup.new_tag('a', href=base + '/blog/' + path + '#content-inner', attrs={'class': 'page-number'})
            item.string = str(number + 1)
            group.append(item)
        nav.append(group)

    added = []
    home_shell = str(read('page/2/index.html'))
    page_count = math.ceil(len(posts) / 10)
    home_files = ['index.html'] + [f'page/{i}/index.html' for i in range(2, page_count + 1)]
    # Regenerate home and archive pages (10 posts each). This avoids
    # displacing the old tenth card or losing any historical post on pagination.
    for index, file in enumerate(home_files):
        soup = read(file) if (blog / file).exists() else fragment(home_shell)
        holder = soup.select_one('#recent-posts')
        for card in holder.select(':scope > .recent-post-item'):
            card.decompose()
        position = holder.select_one(':scope > nav')
        for i, post in enumerate(posts[index * 10:(index + 1) * 10]):
            card = copy.deepcopy(cards[post['path']])
            for badge in card.select('.newPost'):
                badge.decompose()
            card['class'] = [c for c in card.get('class', []) if c != 'lastestpost-item']
            if index == i == 0:
                card['class'].append('lastestpost-item')
                badge = soup.new_tag('span', attrs={'class': 'newPost'})
                badge.string = '最新文章'
                card.select_one('.recent-post-info').insert(0, badge)
            if position:
                position.insert_before(card)
            else:
                holder.append(card)
        paginate(soup, index, page_count, '')
        set_canonical(soup, file.removesuffix('index.html'))
        save(file, soup)
        added.append('blog/' + file.removesuffix('index.html'))

    def fill_listing(soup, subset, heading):
        listing = soup.select_one('.article-sort')
        listing.clear()
        year = None
        for index, post in enumerate(subset):
            if year != post['date'][:4]:
                year = post['date'][:4]
                listing.append(fragment('<div class="article-sort-item year"><span>' + year + '</span></div>'))
            entry = copy.deepcopy(entries[post['path']])
            entry.select_one('.article-sort-item-index').string = str(index + 1)
            listing.append(entry)
        title = soup.select_one('.article-sort-title')
        title.string = heading

    archive_shell = str(read('archives/index.html'))
    archive_files = ['archives/index.html'] + [f'archives/page/{i}/index.html' for i in range(2, page_count + 1)]
    for index, file in enumerate(archive_files):
        soup = read(file) if (blog / file).exists() else fragment(archive_shell)
        fill_listing(soup, posts[index * 10:(index + 1) * 10], '文章总览 - ' + str(len(posts)))
        paginate(soup, index, page_count, 'archives/')
        set_canonical(soup, file.removesuffix('index.html'))
        save(file, soup)
        added.append('blog/' + file.removesuffix('index.html'))
    categories, tags, groups = {}, {}, {}
    for path, card in cards.items():
        category = card.select_one('.article-meta__categories')
        if category:
            key = category.get_text(strip=True)
            categories.setdefault(key, {'path': path_of(category), 'posts': set()})['posts'].add(path)
        for tag in card.select('.article-meta__tags'):
            key = path_of(tag).removeprefix('tags/').strip('/')
            tags.setdefault(key, {'path': 'tags/' + urllib.parse.quote(key, safe='') + '/', 'posts': set()})['posts'].add(path)
    for post in new:
        for name, directory, items in [('分类', 'categories', [post['category']]), ('标签', 'tags', post['tags'])]:
            for key in items:
                info = (categories if directory == 'categories' else tags)[key]
                groups[info['path']] = (name + ' - ' + key, [p for p in posts if p['path'] in info['posts']])
    for date in sorted({part for post in posts for part in (post['date'][:4], post['date'][:7])}):
        groups['archives/' + date.replace('-', '/') + '/'] = (date, [p for p in posts if p['date'].startswith(date)])
    listing_shell = str(read('categories/Python/index.html'))
    for path, (heading, subset) in groups.items():
        count = math.ceil(len(subset) / 10)
        for index in range(count):
            soup = fragment(listing_shell)
            metadata(soup, heading)
            fill_listing(soup, subset[index * 10:(index + 1) * 10], heading + ' - ' + str(len(subset)))
            paginate(soup, index, count, path)
            page_path = path + (f'page/{index + 1}/' if index else '')
            set_canonical(soup, page_path)
            save(page_path + 'index.html', soup)
            added.append('blog/' + page_path)
    # Add category/tag navigation, recent-post and archive links on every page.
    post_indexes = {post['path']: i for i, post in enumerate(posts)}
    for file in blog.rglob('*.html'):
        soup = fragment(file.read_text())
        for holder in soup.select('.category-list'):
            for name, info in categories.items():
                href = base + '/blog/' + info['path']
                existing = next((a for a in holder.select('a') if urllib.parse.unquote(a['href']) == urllib.parse.unquote(href)), None)
                if existing:
                    existing.parent.select_one('.category-list-count').string = str(len(info['posts']))
                else:
                    holder.append(fragment('<li class="category-list-item"><a class="category-list-link" href="' + href + '">' + html.escape(name) + '</a><span class="category-list-count">' + str(len(info['posts'])) + '</span></li>'))
        for holder in soup.select('.tag-cloud-list,.card-tag-cloud'):
            for name, info in tags.items():
                href = base + '/blog/' + info['path']
                existing = next((a for a in holder.select('a') if urllib.parse.unquote(a['href']) == urllib.parse.unquote(href)), None)
                if existing:
                    if existing.sup:
                        existing.sup.string = str(len(info['posts']))
                else:
                    holder.append(fragment('<a href="' + href + '" style="font-size:1.2em">' + html.escape(name) + '<sup>' + str(len(info['posts'])) + '</sup></a>'))
        catalog = soup.select_one('#catalog-list')
        if catalog:
            for name, info in categories.items():
                href = base + '/blog/' + info['path']
                existing = next((a for a in catalog.select('a') if urllib.parse.unquote(a['href']) == urllib.parse.unquote(href)), None)
                if existing:
                    if existing.select_one('.notification-tip'):
                        existing.select_one('.notification-tip').string = str(len(info['posts']))
                else:
                    catalog.append(fragment('<div class="catalog-list-item" id="' + href + '"><a href="' + href + '">' + html.escape(name) + '<span class="notification-tip">' + str(len(info['posts'])) + '</span></a></div>'))
        for archive in soup.select('.card-archive-list'):
            archive.clear()
            for date in sorted({p['date'][:7] for p in posts}, reverse=True):
                href = base + '/blog/archives/' + date.replace('-', '/') + '/'
                count = sum(p['date'].startswith(date) for p in posts)
                month = ['一','二','三','四','五','六','七','八','九','十','十一','十二'][int(date[5:7]) - 1]
                archive.append(fragment('<li class="card-archive-list-item"><a class="card-archive-list-link" href="' + href + '"><span class="card-archive-list-date">' + month + '月 ' + date[:4] + '</span><div class="card-archive-list-count-group"><span class="card-archive-list-count">' + str(count) + '</span><span>篇</span></div></a></li>'))
        for value in soup.select('.site-data a[title="category"] .length-num'):
            value.string = str(len(categories))
        for value in soup.select('.site-data a[title="tag"] .length-num'):
            value.string = str(len(tags))
        for recent in soup.select('.aside-list'):
            recent.clear()
            for post in posts[:5]:
                cover = cards[post['path']].select_one('img')
                cover_url = cover.get('data-lazy-src') or cover['src']
                title = html.escape(post['title'])
                recent.append(fragment('<div class="aside-list-item"><a class="thumbnail" href="' + post_url(post, base) + '"><img src="' + html.escape(cover_url, quote=True) + '" alt="' + title + '" loading="lazy"></a><div class="content"><a class="title" href="' + post_url(post, base) + '">' + title + '</a><time datetime="' + post['date'] + '">' + post['date'] + '</time></div></div>'))
        # Link newly authored notes into the chronological article navigation.
        article = soup.select_one('#article-container')
        article_path = file.parent.relative_to(blog).as_posix() + '/'
        if article and article_path in post_indexes:
            index = post_indexes[article_path]
            neighbors = [('prev', posts[index + 1])] if index + 1 < len(posts) else []
            if index:
                neighbors.append(('next', posts[index - 1]))
            new_paths = {p['path'] for p in new}
            if article_path in new_paths or any(p['path'] in new_paths for _, p in neighbors):
                old_nav = soup.select_one('#pagination')
                if old_nav:
                    old_nav.decompose()
                nav = soup.new_tag('nav', id='pagination', attrs={'class': 'pagination-post'})
                for direction, neighbor in neighbors:
                    cover = cards[neighbor['path']].select_one('img')
                    cover_url = cover.get('data-lazy-src') or cover['src']
                    title = html.escape(neighbor['title'])
                    cls = direction + '-post' + (' pull-full' if len(neighbors) == 1 else '')
                    label = '上一篇' if direction == 'prev' else '下一篇'
                    nav.append(fragment('<div class="' + cls + '"><a href="' + post_url(neighbor, base) + '"><img class="' + direction + '-cover" src="' + html.escape(cover_url, quote=True) + '" alt="' + title + '"><div class="pagination-info"><div class="label">' + label + '</div><div class="' + direction + '_info">' + title + '</div></div></a></div>'))
                soup.select_one('.tag_share').insert_after(nav)
        file.write_text(str(soup))
    # Include all posts in the original random-article feature as well.
    random_js = 'var posts = ' + json.dumps([post_url(p, base) for p in posts], ensure_ascii=False) + ';\nfunction toRandomPost(){pjax.loadUrl(posts[Math.floor(Math.random()*posts.length)]);}\n'
    # Preserve the original function name expected by the navigation.
    (blog / 'anzhiyu/random.js').write_text(random_js)
    return added
