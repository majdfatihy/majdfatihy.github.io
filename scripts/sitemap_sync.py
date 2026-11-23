#!/usr/bin/env python3
"""Manually discover public GitHub Pages URLs; keep creation and lastmod stable."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import urllib.parse as up
import urllib.request as ur
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BASE="https://dev.majdfatihy.com"
OWNER="majdfatihy"
REGISTRY=ROOT/"data/sitemap-registry.json"
SITEMAP=ROOT/"sitemap.xml"
NS="http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)

def today():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()

def norm(raw):
    try:
        p=up.urlsplit(raw)
        if p.scheme!="https" or p.hostname!="dev.majdfatihy.com" or p.port not in (None,443) or p.username:
            return None
        path=up.unquote(p.path or "/")
        if "\\" in path or "//" in path or any(v in (".","..") for v in path.split("/")):
            return None
        if path.endswith("/index.html"):
            path=path[:-len("index.html")]
        if not (path.endswith("/") or path.endswith(".html")):
            return None
        return BASE+up.quote(path,safe="/-._~")
    except ValueError:
        return None

def get(url, api=False, cap=3000000):
    h={"User-Agent":"majd-manual-sitemap-sync/1.0",
       "Accept":"application/vnd.github+json" if api else "text/html,application/xml;q=0.9"}
    if api and os.environ.get("GITHUB_TOKEN"):
        h["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
        h["X-GitHub-Api-Version"]="2022-11-28"
    with ur.urlopen(ur.Request(url,headers=h),timeout=12) as response:
        body=response.read(cap+1)
        if len(body)>cap:
            raise ValueError("Response exceeds safe size")
        return body,response.geturl(),response.headers

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical=None
        self.robots=[]
        self.links=[]
        self.title=[]
        self.description=""
        self.text=[]
        self.skip=0
        self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("script","style","noscript","svg"):
            self.skip+=1
        if tag=="title":
            self.in_title=True
        if tag=="link":
            rel=(a.get("rel") or "").lower().split()
            if "canonical" in rel and a.get("href"):
                self.canonical=a["href"].strip()
            if "alternate" in rel and a.get("hreflang") and a.get("href"):
                self.links.append(a["href"])
        if tag=="a" and a.get("href"):
            self.links.append(a["href"])
        if tag=="meta":
            name=(a.get("name") or "").lower()
            if name in ("robots","googlebot"):
                self.robots.append((a.get("content") or "").lower())
            if name=="description":
                self.description=a.get("content") or ""
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg"):
            self.skip=max(0,self.skip-1)
        if tag=="title":
            self.in_title=False
    def handle_data(self,data):
        if self.in_title:
            self.title.append(data)
        if not self.skip and data.strip():
            self.text.append(data)

def inspect(url):
    raw,final,headers=get(url)
    if norm(final)!=url:
        return None,"redirect mismatch: "+final
    if "text/html" not in headers.get("Content-Type","").lower():
        return None,"not HTML"
    if "noindex" in headers.get("X-Robots-Tag","").lower():
        return None,"X-Robots-Tag noindex"
    page=Page()
    page.feed(raw.decode("utf-8","replace"))
    if any(re.search(r"(?:^|[\s,])noindex(?:[\s,]|$)",x) for x in page.robots):
        return None,"robots meta noindex"
    if not page.canonical:
        return None,"missing canonical"
    if norm(up.urljoin(url,page.canonical))!=url:
        return None,"canonical mismatch: "+page.canonical
    body=" ".join(" ".join(page.text).split())
    title=" ".join(" ".join(page.title).split())
    if len(body)<120:
        return None,"short content"
    digest=hashlib.sha256((title+"\n"+page.description+"\n"+body).encode("utf-8")).hexdigest()
    links=[]
    for href in page.links:
        target=norm(up.urljoin(url,href))
        if target and target not in links:
            links.append(target)
    return {"hash":digest,"links":links},None

def github_repos():
    for page in range(1,21):
        raw,_,_=get(f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}",api=True)
        rows=json.loads(raw)
        if not isinstance(rows,list):
            raise RuntimeError("GitHub API unavailable")
        yield from rows
        if len(rows)<100:
            return
    raise RuntimeError("Repository pagination exceeded limit")

def source_path(url):
    tail=url.removeprefix(BASE+"/")
    if not tail:
        return OWNER+".github.io","index.html"
    parts=tail.split("/")
    if len(parts)==1 and parts[0].endswith(".html"):
        return OWNER+".github.io",parts[0]
    child="/".join(parts[1:])
    return parts[0],(child+"index.html" if not child or child.endswith("/") else child)

def git_file_dates(url):
    repo,path=source_path(url)
    first=latest=None
    for page in range(1,21):
        endpoint=(f"https://api.github.com/repos/{OWNER}/{up.quote(repo,safe='-._~')}"
                  f"/commits?path={up.quote(path,safe='/')}&per_page=100&page={page}")
        try:
            raw,_,_=get(endpoint,api=True,cap=2000000)
            rows=json.loads(raw)
        except (OSError,ValueError):
            return None,None
        if not isinstance(rows,list) or not rows:
            break
        if latest is None:
            latest=rows[0].get("commit",{}).get("committer",{}).get("date","")[:10]
        first=rows[-1].get("commit",{}).get("committer",{}).get("date","")[:10]
        if len(rows)<100:
            break
    isdate=lambda s: bool(s and re.fullmatch(r"\d{4}-\d{2}-\d{2}",s))
    return first if isdate(first) else None,latest if isdate(latest) else None

def load_registry():
    data=json.loads(REGISTRY.read_text("utf-8")) if REGISTRY.exists() else {"schema_version":1,"pages":{}}
    if data.get("schema_version")!=1 or not isinstance(data.get("pages"),dict):
        raise ValueError("Unknown sitemap registry structure")
    return data

def collect_urls(data):
    urls=set(data["pages"])
    if SITEMAP.exists():
        xml=ET.parse(SITEMAP).getroot()
        for item in xml.findall(f"{{{NS}}}url"):
            url=norm(item.findtext(f"{{{NS}}}loc") or "")
            if url:
                urls.add(url)
                modified=item.findtext(f"{{{NS}}}lastmod")
                if modified:
                    data["pages"].setdefault(url,{}).setdefault("lastmod",modified)
    site=json.loads((ROOT/"data/site.json").read_text("utf-8"))
    for page in site["pages"]:
        loc=BASE+"/" if page["slug"]=="index" else f"{BASE}/{page['slug']}.html"
        urls.add(loc)
    projects=json.loads((ROOT/"data/projects.json").read_text("utf-8"))
    for project in projects["projects"]:
        loc=norm(project["url"])
        if loc:
            urls.add(loc)
    return urls

def record_page(data,url,digest,now):
    item=data["pages"].setdefault(url,{})
    item.setdefault("first_seen",now) # Tracking date; not historical publication date.
    item.setdefault("created_at",None)
    prior=item.get("hash")
    if digest and (digest!=prior or not item["created_at"]):
        created,modified=git_file_dates(url)
        if created and not item["created_at"]:
            item["created_at"]=created
            item["creation_source"]="first_git_commit_for_page_file"
        if prior and prior!=digest:
            previous=item.get("lastmod")
            item["lastmod"]=modified if modified and (not previous or modified>=previous) else now
        elif not prior and modified:
            item["lastmod"]=modified
    if digest:
        item["hash"]=digest

def sitemap_links(root):
    try:
        raw,_,headers=get(root+"sitemap.xml",cap=1000000)
        if "xml" not in headers.get("Content-Type","").lower():
            return []
        xml=ET.fromstring(raw)
        return [url for node in xml.iter() if node.tag.endswith("}loc")
                if (url:=norm(node.text or "")) and url.startswith(root)][:100]
    except (OSError,ValueError,ET.ParseError):
        return []

def discover(data):
    now=today()
    robots=urllib.robotparser.RobotFileParser()
    try:
        raw,_,_=get(BASE+"/robots.txt",cap=200000)
        robots.parse(raw.decode("utf-8","replace").splitlines())
    except (OSError,ValueError) as error:
        raise RuntimeError("Cannot verify robots.txt; no files were modified") from error
    known=collect_urls(data)
    found=set()
    skipped=[]
    roots=[]
    for repo in github_repos():
        if repo.get("private") or repo.get("archived") or repo.get("fork") or not repo.get("has_pages"):
            continue
        name=repo.get("name","")
        if name==OWNER+".github.io":
            continue
        root=norm(BASE+"/"+up.quote(name,safe="-._~")+"/")
        if root:
            roots.append(root)
    for root in roots:
        queue=[root]+sitemap_links(root)
        visited=set()
        while queue and len(visited)<30:
            url=queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if not robots.can_fetch("Googlebot",url):
                skipped.append((url,"robots.txt blocks crawling"))
                continue
            try:
                page,reason=inspect(url)
            except (OSError,ValueError,UnicodeError) as error:
                page,reason=None,str(error)
            if not page:
                skipped.append((url,reason))
                continue
            found.add(url)
            record_page(data,url,page["hash"],now)
            for link in page["links"]:
                if link.startswith(root) and link not in visited and link not in queue:
                    queue.append(link)
    # Previously listed URLs are never removed, even if later unreachable.
    for url in sorted(known-found):
        if robots.can_fetch("Googlebot",url):
            try:
                page,_=inspect(url)
                if page:
                    record_page(data,url,page["hash"],now)
            except (OSError,ValueError,UnicodeError):
                pass
    for url in sorted(known|found):
        item=data["pages"].setdefault(url,{})
        item.setdefault("first_seen",now)
        if not item.get("created_at"):
            created,_=git_file_dates(url)
            if created:
                item["created_at"]=created
                item["creation_source"]="first_git_commit_for_page_file"
        item.setdefault("created_at",None)
    new=sorted(found-known)
    print(f"Public Pages roots={len(roots)}; existing={len(known)}; newly found={len(new)}")
    for url in new:
        print("ADDED",url)
    for url,reason in skipped:
        print("SKIPPED",url,reason)

def render(data):
    urls=collect_urls(data)
    for url in urls:
        data["pages"].setdefault(url,{})
    if SITEMAP.exists():
        previous={}
        for node in ET.parse(SITEMAP).getroot().findall(f"{{{NS}}}url"):
            url=norm(node.findtext(f"{{{NS}}}loc") or "")
            if url:
                previous[url]=node.findtext(f"{{{NS}}}lastmod")
        if set(previous)==urls and all(previous[url]==data["pages"][url].get("lastmod") for url in urls):
            print(f"Unchanged sitemap: {len(urls)} URLs")
            return
    doc=ET.Element(f"{{{NS}}}urlset")
    for url in sorted(urls):
        entry=ET.SubElement(doc,f"{{{NS}}}url")
        ET.SubElement(entry,f"{{{NS}}}loc").text=url
        modified=data["pages"][url].get("lastmod")
        if modified and re.fullmatch(r"\d{4}-\d{2}-\d{2}",modified):
            ET.SubElement(entry,f"{{{NS}}}lastmod").text=modified
    body='<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(doc,encoding="unicode")+"\n"
    SITEMAP.write_text(body,"utf-8")
    print(f"Updated sitemap: {len(urls)} URLs")

def main():
    cli=argparse.ArgumentParser()
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover",action="store_true")
    mode.add_argument("--render",action="store_true")
    args=cli.parse_args()
    data=load_registry()
    if args.discover:
        discover(data)
        new=json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
        if not REGISTRY.exists() or REGISTRY.read_text("utf-8")!=new:
            REGISTRY.parent.mkdir(parents=True,exist_ok=True)
            REGISTRY.write_text(new,"utf-8")
    render(data)

if __name__=="__main__":
    main()
