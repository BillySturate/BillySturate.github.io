"""Render only the blog About page, preserving the surrounding theme shell."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]

def render_about(soup, base, config):
    data = json.loads((ROOT / 'data/blog-about.json').read_text())
    for photo in data['travel_photos']:
        path = (ROOT / photo['src'].lstrip('/')).resolve()
        if not path.is_relative_to(ROOT / 'assets/blog/travel') or not path.is_file():
            raise ValueError('Travel photo must be an existing file in assets/blog/travel: ' + photo['src'])
    # Remove the retired About-only greeting/statistics/GSAP initializer; its
    # original DOM no longer exists. Global navigation and star effects remain.
    for script in list(soup.select('script:not([src])')):
        if script.string and 'var pursuitInterval' in script.string:
            script.decompose()
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=select_autoescape())
    markup = env.get_template('blog-about.html').render(about=data, config=config, base=base)
    soup.select_one('#about-page').replace_with(BeautifulSoup(markup, 'html.parser'))
    soup.body['class'] = soup.body.get('class', []) + ['blog-about-v2']
    soup.select_one('#about-page').insert(0, soup.new_tag('link', rel='stylesheet', href=base + '/assets/blog-about.css'))
    # CSS stars supplement the retained global effect and respect reduced motion.
    stars = soup.new_tag('div', attrs={'class': 'ba-stars', 'aria-hidden': 'true'})
    soup.select_one('#about-page').insert(0, stars)
    for tag in soup.select('meta[name="description"],meta[property="og:description"]'):
        tag['content'] = data['subtitle'] + ' ' + data['intro']
