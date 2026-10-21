#!/usr/bin/env python3
"""يبني كل صفحات الموقع من data/ + content/ — شغّله بالأمر:  python build.py
إضافة مشروع جديد: أضف كتلة جديدة في data/projects.json ثم شغّل الأمر.
(اختياري) تاريخ مخصص:  python build.py --date 2026-10-22"""
import json, re, sys, html, datetime, pathlib

ROOT = pathlib.Path(__file__).parent
S = json.loads((ROOT / 'data/site.json').read_text('utf-8'))
PR = json.loads((ROOT / 'data/projects.json').read_text('utf-8'))
TODAY = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else datetime.date.today().isoformat()
BASE = S['url'].rstrip('/')
E = lambda s: html.escape(str(s), quote=True)
CATS = {c['id']: c['label'] for c in PR['categories']}
OG = f'{BASE}/assets/img/og-image.png'


def url_of(slug):
    return BASE + '/' if slug == 'index' else f'{BASE}/{slug}.html'


def ad(name):
    return f'<div class="ad-zone" data-ad="{name}"></div>'


def project_cards():
    out = []
    for p in PR['projects']:
        ext = not p['url'].startswith(BASE)
        tg = ' target="_blank" rel="noopener"' if ext else ''
        tags = ''.join(f'<span>{E(t)}</span>' for t in p.get('tags', []))
        hay = ' '.join([p['title'], p['description'], ' '.join(p.get('tags', [])), CATS.get(p['category'], '')])
        out.append(
            f'<a class="proj" href="{E(p["url"])}"{tg} data-cat="{E(p["category"])}" data-s="{E(hay.lower())}">'
            f'<span class="ico" aria-hidden="true">{p["icon"]}</span>'
            f'<span class="badge">{E(CATS.get(p["category"], ""))}</span>'
            f'<h3>{E(p["title"])}</h3><p>{E(p["description"])}</p>'
            f'<span class="tags">{tags}</span><span class="go">{E(p.get("cta", "افتح المشروع"))}</span></a>')
    return '<div class="grid-proj" id="projectsGrid">' + ''.join(out) + '</div>'


def chips():
    b = '<button type="button" class="chip" data-f="all" aria-pressed="true">الكل</button>'
    for c in PR['categories']:
        b += f'<button type="button" class="chip" data-f="{E(c["id"])}" aria-pressed="false">{E(c["label"])}</button>'
    return f'<div class="chips" role="group" aria-label="تصفية حسب النوع">{b}</div>'


def jsonld(pg):
    person = {'@type': 'Person', '@id': BASE + '/#author', 'name': S['author'], 'url': BASE + '/',
              'jobTitle': S['author_role'], 'sameAs': [x['url'] for x in S['social']]}
    page = {'@type': pg['type'], '@id': url_of(pg['slug']) + '#webpage', 'url': url_of(pg['slug']),
            'name': pg['title'], 'description': pg['description'], 'inLanguage': S['lang'],
            'isPartOf': {'@id': BASE + '/#website'}, 'author': {'@id': BASE + '/#author'},
            'dateModified': TODAY, 'primaryImageOfPage': {'@type': 'ImageObject', 'url': OG, 'width': 1200, 'height': 630}}
    g = []
    if pg['slug'] == 'index':
        g.append({'@type': 'WebSite', '@id': BASE + '/#website', 'url': BASE + '/', 'name': S['name'],
                  'alternateName': [S['name_en']] + S['alt_names'], 'inLanguage': S['lang'],
                  'publisher': {'@id': BASE + '/#author'}})
        g.append(person)
        g.append(page)
        g.append({'@type': 'ItemList', 'name': 'المشاريع والأدوات', 'numberOfItems': len(PR['projects']),
                  'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': p['title'], 'url': p['url']}
                                      for i, p in enumerate(PR['projects'])]})
    else:
        g.append(page)
        g.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'الرئيسية', 'item': BASE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': pg['title'].split('|')[0].strip(), 'item': url_of(pg['slug'])}]})
    return json.dumps({'@context': 'https://schema.org', '@graph': g}, ensure_ascii=False)


def head(pg, noindex=False):
    t, d, u = pg['title'], pg['description'], url_of(pg['slug'])
    robots = 'noindex,follow' if noindex else 'index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1'
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={S["ga_id"]}"></script>'
          f'<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{S["ga_id"]}");</script>') if S.get('ga_id') else ''
    return f'''<!DOCTYPE html>
<html lang="{S['lang']}" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(t)}</title>
<meta name="description" content="{E(d)}">
<meta name="author" content="{E(S['author'])}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="{S['theme_color']}">
<meta name="color-scheme" content="dark">
<link rel="canonical" href="{u}">
<link rel="alternate" hreflang="{S['lang']}" href="{u}">
<link rel="alternate" hreflang="x-default" href="{u}">
<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml" sizes="any">
<link rel="icon" href="assets/img/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<meta property="og:type" content="website">
<meta property="og:locale" content="{S['locale']}">
<meta property="og:site_name" content="{E(S['name'])}">
<meta property="og:title" content="{E(t)}">
<meta property="og:description" content="{E(d)}">
<meta property="og:url" content="{u}">
<meta property="og:image" content="{OG}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(S['name_en'])} - {E(S['tagline'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(t)}">
<meta name="twitter:description" content="{E(d)}">
<meta name="twitter:image" content="{OG}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/site.css">
<script type="application/ld+json">{jsonld(pg)}</script>
{ga}
</head>
<body>
'''


def header(cur):
    nav = ''.join(
        f'<a href="{E(n["href"])}"' + (' aria-current="page"' if n['href'].split('#')[0] == cur and '#' not in n['href'] else '') + f'>{E(n["label"])}</a>'
        for n in S['nav'])
    return f'''<a class="skip" href="#main">انتقل إلى المحتوى</a>
<canvas id="bgNet" aria-hidden="true"></canvas>
<header class="site-header"><div class="wrap bar">
<a class="brand" href="index.html" aria-label="{E(S['name'])} - الصفحة الرئيسية"><img src="assets/img/icon-192.png" width="38" height="38" alt=""><span><b>{E(S['name'])}</b><small>{E(S['name_en'])}</small></span></a>
<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav" aria-label="فتح القائمة"><span></span><span></span><span></span></button>
<nav id="nav" class="nav" aria-label="القائمة الرئيسية">{nav}</nav>
</div></header>
{ad('topx')}
<main id="main">
'''


def footer():
    soc = ''.join(f'<a href="{E(x["url"])}" rel="noopener me" target="_blank">{E(x["label"])}</a>' for x in S['social'])
    quick = ''.join(f'<li><a href="{E(n["href"])}">{E(n["label"])}</a></li>' for n in S['nav'])
    legal = ''.join(f'<li><a href="{E(n["href"])}">{E(n["label"])}</a></li>' for n in S['legal'])
    src = ''.join(f'<li><a href="{E(n["url"])}" rel="noopener" target="_blank">{E(n["label"])}</a></li>' for n in S['sources'])
    year = TODAY[:4]
    return f'''</main>
<div class="wrap">{ad('seo')}{ad('end')}</div>
<footer class="site-footer"><div class="wrap foot-grid">
<section><p class="f-title">{E(S['name'])}</p><p>{E(S['footer_blurb'])}</p><div class="social">{soc}</div></section>
<nav aria-label="روابط سريعة"><p class="f-title">روابط سريعة</p><ul>{quick}</ul></nav>
<nav aria-label="الصفحات القانونية"><p class="f-title">الصفحات القانونية</p><ul>{legal}</ul></nav>
<nav aria-label="مصادر رسمية"><p class="f-title">مصادر رسمية</p><ul>{src}</ul></nav>
</div><p class="copy">© {year} {E(S['name'])} · {E(S['name_en'])} · جميع الحقوق محفوظة</p></footer>
<button id="bgToggle" class="bg-toggle" type="button" aria-pressed="false" aria-label="إيقاف حركة الخلفية" title="إيقاف/تشغيل حركة الخلفية"><span class="ic" aria-hidden="true"></span></button>
<script src="assets/js/ads.js" defer></script>
<script src="assets/js/site.js" defer></script>
</body>
</html>
'''


def words(fragment):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', fragment, flags=re.S)
    return len(re.findall(r'[\w\u0600-\u06FF]+', re.sub(r'<[^>]+>', ' ', t)))


def render(body):
    rep = {'{{PROJECTS_GRID}}': project_cards(), '{{CHIPS}}': chips(), '{{PROJECT_COUNT}}': str(len(PR['projects'])),
           '{{EMAIL}}': S['email']}
    for k, v in rep.items():
        body = body.replace(k, v)
    return re.sub(r'\{\{AD:(\w+)\}\}', lambda m: ad(m.group(1)), body)


def main():
    report = []
    for pg in S['pages']:
        body = render((ROOT / f'content/{pg["file"]}.html').read_text('utf-8'))
        out = head(pg) + header(pg['slug'] + '.html') + body + footer()
        (ROOT / f'{pg["slug"]}.html').write_text(out, 'utf-8')
        n = words(body)
        report.append((pg['slug'], n))
        if n < 400:
            print(f'تحذير: صفحة {pg["slug"]} فيها {n} كلمة فقط (أقل من 400)')
    nf = {'slug': '404', 'title': 'الصفحة غير موجودة | ' + S['name'], 'description': 'الصفحة المطلوبة غير موجودة.', 'type': 'WebPage'}
    (ROOT / '404.html').write_text(head(nf, True).replace('<canvas', '<canvas') + header('404.html') +
                                   render((ROOT / 'content/404.html').read_text('utf-8')) + footer(), 'utf-8')

    # sitemap.xml: صفحات الموقع + مشاريع نفس النطاق
    urls = [(url_of(p['slug']), p['priority'], p['freq']) for p in S['pages']]
    urls += [(p['url'], '0.8', 'weekly') for p in PR['projects'] if p['url'].startswith(BASE)]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, fr in urls:
        sm.append(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod><changefreq>{fr}</changefreq><priority>{pr}</priority></url>')
    sm.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(sm) + '\n', 'utf-8')

    # llms.txt
    L = [f'# {S["name"]} ({S["name_en"]})', '', f'> {S["tagline"]}. {S["footer_blurb"]}', '',
         f'الموقع الرسمي: {BASE}/', '', '## المشاريع والأدوات']
    L += [f'- [{p["title"]}]({p["url"]}): {p["description"]}' for p in PR['projects']]
    L += ['', '## صفحات الموقع'] + [f'- [{p["title"].split("|")[0].strip()}]({url_of(p["slug"])}): {p["description"]}' for p in S['pages'][1:]]
    L += ['', '## التواصل', f'- البريد: {S["email"]}'] + [f'- {x["label"]}: {x["url"]}' for x in S['social']]
    (ROOT / 'llms.txt').write_text('\n'.join(L) + '\n', 'utf-8')

    # robots.txt (كل الزواحف مسموحة، بما فيها زواحف الذكاء الاصطناعي)
    bots = ['OAI-SearchBot', 'ChatGPT-User', 'GPTBot', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
            'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'bingbot', 'Googlebot']
    R = ['# السماح لجميع الزواحف، بما فيها زواحف محركات البحث وأدوات الذكاء الاصطناعي', 'User-agent: *', 'Allow: /', '']
    for b in bots:
        R += [f'User-agent: {b}', 'Allow: /', '']
    R += [f'Sitemap: {BASE}/sitemap.xml']
    (ROOT / 'robots.txt').write_text('\n'.join(R) + '\n', 'utf-8')

    (ROOT / 'site.webmanifest').write_text(json.dumps({
        'name': f'{S["name"]} | {S["name_en"]}', 'short_name': S['name'], 'lang': S['lang'], 'dir': 'rtl',
        'start_url': './', 'display': 'standalone', 'background_color': S['theme_color'], 'theme_color': S['theme_color'],
        'icons': [{'src': 'assets/img/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                  {'src': 'assets/img/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'}]},
        ensure_ascii=False, indent=2), 'utf-8')
    (ROOT / '.nojekyll').write_text('', 'utf-8')
    print('تم البناء:', ', '.join(f'{s}={n} كلمة' for s, n in report))


main()
