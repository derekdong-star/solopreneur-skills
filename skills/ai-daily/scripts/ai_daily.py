#!/usr/bin/env python3
"""
AI Daily Digest - AI-powered RSS digest from 90 top tech blogs

Fetches RSS feeds from Hacker News Popularity Contest 2025 (curated by Karpathy),
uses AI to score and filter articles, and generates a daily digest in Markdown.
"""

import os
import sys
import json
import re
import argparse
import asyncio
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl


# ============================================================================
# Constants
# ============================================================================

OPENAI_DEFAULT_API_BASE = "https://open.bigmodel.cn/api/paas/v4/"
OPENAI_DEFAULT_MODEL = "glm-4.7"
FEED_FETCH_TIMEOUT = 15
FEED_CONCURRENCY = 10
BATCH_SIZE = 10
MAX_CONCURRENT_REQUESTS = 2

# 90 RSS feeds from Hacker News Popularity Contest 2025 (curated by Karpathy)
RSS_FEEDS = [
    {"name": "simonwillison.net", "xmlUrl": "https://simonwillison.net/atom/everything/", "htmlUrl": "https://simonwillison.net"},
    {"name": "jeffgeerling.com", "xmlUrl": "https://www.jeffgeerling.com/blog.xml", "htmlUrl": "https://jeffgeerling.com"},
    {"name": "seangoedecke.com", "xmlUrl": "https://www.seangoedecke.com/rss.xml", "htmlUrl": "https://seangoedecke.com"},
    {"name": "krebsonsecurity.com", "xmlUrl": "https://krebsonsecurity.com/feed/", "htmlUrl": "https://krebsonsecurity.com"},
    {"name": "daringfireball.net", "xmlUrl": "https://daringfireball.net/feeds/main", "htmlUrl": "https://daringfireball.net"},
    {"name": "ericmigi.com", "xmlUrl": "https://ericmigi.com/rss.xml", "htmlUrl": "https://ericmigi.com"},
    {"name": "antirez.com", "xmlUrl": "http://antirez.com/rss", "htmlUrl": "http://antirez.com"},
    {"name": "idiallo.com", "xmlUrl": "https://idiallo.com/feed.rss", "htmlUrl": "https://idiallo.com"},
    {"name": "maurycyz.com", "xmlUrl": "https://maurycyz.com/index.xml", "htmlUrl": "https://maurycyz.com"},
    {"name": "pluralistic.net", "xmlUrl": "https://pluralistic.net/feed/", "htmlUrl": "https://pluralistic.net"},
    {"name": "shkspr.mobi", "xmlUrl": "https://shkspr.mobi/blog/feed/", "htmlUrl": "https://shkspr.mobi"},
    {"name": "lcamtuf.substack.com", "xmlUrl": "https://lcamtuf.substack.com/feed", "htmlUrl": "https://lcamtuf.substack.com"},
    {"name": "mitchellh.com", "xmlUrl": "https://mitchellh.com/feed.xml", "htmlUrl": "https://mitchellh.com"},
    {"name": "dynomight.net", "xmlUrl": "https://dynomight.net/feed.xml", "htmlUrl": "https://dynomight.net"},
    # {"name": "utcc.utoronto.ca/~cks", "xmlUrl": "https://utcc.utoronto.ca/~cks/space/blog/?atom", "htmlUrl": "https://utcc.utoronto.ca/~cks"},
    {"name": "xeiaso.net", "xmlUrl": "https://xeiaso.net/blog.rss", "htmlUrl": "https://xeiaso.net"},
    {"name": "devblogs.microsoft.com/oldnewthing", "xmlUrl": "https://devblogs.microsoft.com/oldnewthing/feed", "htmlUrl": "https://devblogs.microsoft.com/oldnewthing"},
    {"name": "righto.com", "xmlUrl": "https://www.righto.com/feeds/posts/default", "htmlUrl": "https://righto.com"},
    {"name": "lucumr.pocoo.org", "xmlUrl": "https://lucumr.pocoo.org/feed.atom", "htmlUrl": "https://lucumr.pocoo.org"},
    {"name": "skyfall.dev", "xmlUrl": "https://skyfall.dev/rss.xml", "htmlUrl": "https://skyfall.dev"},
    {"name": "garymarcus.substack.com", "xmlUrl": "https://garymarcus.substack.com/feed", "htmlUrl": "https://garymarcus.substack.com"},
    # {"name": "rachelbythebay.com", "xmlUrl": "https://rachelbythebay.com/w/atom.xml", "htmlUrl": "https://rachelbythebay.com"},
    {"name": "overreacted.io", "xmlUrl": "https://overreacted.io/rss.xml", "htmlUrl": "https://overreacted.io"},
    {"name": "timsh.org", "xmlUrl": "https://timsh.org/rss/", "htmlUrl": "https://timsh.org"},
    {"name": "johndcook.com", "xmlUrl": "https://www.johndcook.com/blog/feed/", "htmlUrl": "https://johndcook.com"},
    {"name": "gilesthomas.com", "xmlUrl": "https://gilesthomas.com/feed/rss.xml", "htmlUrl": "https://gilesthomas.com"},
    {"name": "matklad.github.io", "xmlUrl": "https://matklad.github.io/feed.xml", "htmlUrl": "https://matklad.github.io"},
    {"name": "derekthompson.org", "xmlUrl": "https://www.theatlantic.com/feed/author/derek-thompson/", "htmlUrl": "https://derekthompson.org"},
    {"name": "evanhahn.com", "xmlUrl": "https://evanhahn.com/feed.xml", "htmlUrl": "https://evanhahn.com"},
    {"name": "terriblesoftware.org", "xmlUrl": "https://terriblesoftware.org/feed/", "htmlUrl": "https://terriblesoftware.org"},
    {"name": "rakhim.exotext.com", "xmlUrl": "https://rakhim.exotext.com/rss.xml", "htmlUrl": "https://rakhim.exotext.com"},
    {"name": "joanwestenberg.com", "xmlUrl": "https://joanwestenberg.com/rss", "htmlUrl": "https://joanwestenberg.com"},
    {"name": "xania.org", "xmlUrl": "https://xania.org/feed", "htmlUrl": "https://xania.org"},
    {"name": "micahflee.com", "xmlUrl": "https://micahflee.com/feed/", "htmlUrl": "https://micahflee.com"},
    {"name": "nesbitt.io", "xmlUrl": "https://nesbitt.io/feed.xml", "htmlUrl": "https://nesbitt.io"},
    {"name": "construction-physics.com", "xmlUrl": "https://www.construction-physics.com/feed", "htmlUrl": "https://construction-physics.com"},
    {"name": "tedium.co", "xmlUrl": "https://feed.tedium.co/", "htmlUrl": "https://tedium.co"},
    {"name": "susam.net", "xmlUrl": "https://susam.net/feed.xml", "htmlUrl": "https://susam.net"},
    {"name": "entropicthoughts.com", "xmlUrl": "https://entropicthoughts.com/feed.xml", "htmlUrl": "https://entropicthoughts.com"},
    {"name": "buttondown.com/hillelwayne", "xmlUrl": "https://buttondown.com/hillelwayne/rss", "htmlUrl": "https://buttondown.com/hillelwayne"},
    {"name": "dwarkesh.com", "xmlUrl": "https://www.dwarkeshpatel.com/feed", "htmlUrl": "https://dwarkesh.com"},
    {"name": "borretti.me", "xmlUrl": "https://borretti.me/feed.xml", "htmlUrl": "https://borretti.me"},
    {"name": "wheresyoured.at", "xmlUrl": "https://www.wheresyoured.at/rss/", "htmlUrl": "https://wheresyoured.at"},
    {"name": "jayd.ml", "xmlUrl": "https://jayd.ml/feed.xml", "htmlUrl": "https://jayd.ml"},
    {"name": "minimaxir.com", "xmlUrl": "https://minimaxir.com/index.xml", "htmlUrl": "https://minimaxir.com"},
    {"name": "geohot.github.io", "xmlUrl": "https://geohot.github.io/blog/feed.xml", "htmlUrl": "https://geohot.github.io"},
    {"name": "paulgraham.com", "xmlUrl": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "htmlUrl": "https://paulgraham.com"},
    {"name": "filfre.net", "xmlUrl": "https://www.filfre.net/feed/", "htmlUrl": "https://filfre.net"},
    {"name": "blog.jim-nielsen.com", "xmlUrl": "https://blog.jim-nielsen.com/feed.xml", "htmlUrl": "https://blog.jim-nielsen.com"},
    # {"name": "dfarq.homeip.net", "xmlUrl": "https://dfarq.homeip.net/feed/", "htmlUrl": "https://dfarq.homeip.net"},
    {"name": "jyn.dev", "xmlUrl": "https://jyn.dev/atom.xml", "htmlUrl": "https://jyn.dev"},
    {"name": "geoffreylitt.com", "xmlUrl": "https://www.geoffreylitt.com/feed.xml", "htmlUrl": "https://geoffreylitt.com"},
    {"name": "downtowndougbrown.com", "xmlUrl": "https://www.downtowndougbrown.com/feed/", "htmlUrl": "https://www.downtowndougbrown.com"},
    {"name": "brutecat.com", "xmlUrl": "https://brutecat.com/rss.xml", "htmlUrl": "https://brutecat.com"},
    {"name": "eli.thegreenplace.net", "xmlUrl": "https://eli.thegreenplace.net/feeds/all.atom.xml", "htmlUrl": "https://eli.thegreenplace.net"},
    {"name": "abortretry.fail", "xmlUrl": "https://www.abortretry.fail/feed", "htmlUrl": "https://abortretry.fail"},
    {"name": "fabiensanglard.net", "xmlUrl": "https://fabiensanglard.net/rss.xml", "htmlUrl": "https://fabiensanglard.net"},
    {"name": "oldvcr.blogspot.com", "xmlUrl": "https://oldvcr.blogspot.com/feeds/posts/default", "htmlUrl": "https://oldvcr.blogspot.com"},
    {"name": "bogdanthegeek.github.io", "xmlUrl": "https://bogdanthegeek.github.io/blog/index.xml", "htmlUrl": "https://bogdanthegeek.github.io"},
    {"name": "hugotunius.se", "xmlUrl": "https://hugotunius.se/feed.xml", "htmlUrl": "https://hugotunius.se"},
    {"name": "gwern.net", "xmlUrl": "https://gwern.substack.com/feed", "htmlUrl": "https://gwern.net"},
    {"name": "berthub.eu", "xmlUrl": "https://berthub.eu/articles/index.xml", "htmlUrl": "https://berthub.eu"},
    {"name": "chadnauseam.com", "xmlUrl": "https://chadnauseam.com/rss.xml", "htmlUrl": "https://chadnauseam.com"},
    {"name": "simone.org", "xmlUrl": "https://simone.org/feed/", "htmlUrl": "https://simone.org"},
    {"name": "it-notes.dragas.net", "xmlUrl": "https://it-notes.dragas.net/feed/", "htmlUrl": "https://it-notes.dragas.net"},
    {"name": "beej.us", "xmlUrl": "https://beej.us/blog/rss.xml", "htmlUrl": "https://beej.us"},
    {"name": "hey.paris", "xmlUrl": "https://hey.paris/index.xml", "htmlUrl": "https://hey.paris"},
    {"name": "danielwirtz.com", "xmlUrl": "https://danielwirtz.com/rss.xml", "htmlUrl": "https://danielwirtz.com"},
    {"name": "matduggan.com", "xmlUrl": "https://matduggan.com/rss/", "htmlUrl": "https://matduggan.com"},
    {"name": "refactoringenglish.com", "xmlUrl": "https://refactoringenglish.com/index.xml", "htmlUrl": "https://refactoringenglish.com"},
    {"name": "worksonmymachine.substack.com", "xmlUrl": "https://worksonmymachine.substack.com/feed", "htmlUrl": "https://worksonmymachine.substack.com"},
    {"name": "philiplaine.com", "xmlUrl": "https://philiplaine.com/index.xml", "htmlUrl": "https://philiplaine.com"},
    {"name": "steveblank.com", "xmlUrl": "https://steveblank.com/feed/", "htmlUrl": "https://steveblank.com"},
    {"name": "bernsteinbear.com", "xmlUrl": "https://bernsteinbear.com/feed.xml", "htmlUrl": "https://bernsteinbear.com"},
    {"name": "danieldelaney.net", "xmlUrl": "https://danieldelaney.net/feed", "htmlUrl": "https://danieldelaney.net"},
    {"name": "troyhunt.com", "xmlUrl": "https://www.troyhunt.com/rss/", "htmlUrl": "https://troyhunt.com"},
    {"name": "herman.bearblog.dev", "xmlUrl": "https://herman.bearblog.dev/feed/", "htmlUrl": "https://herman.bearblog.dev"},
    {"name": "tomrenner.com", "xmlUrl": "https://tomrenner.com/index.xml", "htmlUrl": "https://tomrenner.com"},
    {"name": "blog.pixelmelt.dev", "xmlUrl": "https://blog.pixelmelt.dev/rss/", "htmlUrl": "https://blog.pixelmelt.dev"},
    {"name": "martinalderson.com", "xmlUrl": "https://martinalderson.com/feed.xml", "htmlUrl": "https://martinalderson.com"},
    {"name": "danielchasehooper.com", "xmlUrl": "https://danielchasehooper.com/feed.xml", "htmlUrl": "https://danielchasehooper.com"},
    {"name": "chiark.greenend.org.uk/~sgtatham", "xmlUrl": "https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/feed.xml", "htmlUrl": "https://chiark.greenend.org.uk/~sgtatham"},
    {"name": "grantslatton.com", "xmlUrl": "https://grantslatton.com/rss.xml", "htmlUrl": "https://grantslatton.com"},
    {"name": "experimental-history.com", "xmlUrl": "https://www.experimental-history.com/feed", "htmlUrl": "https://experimental-history.com"},
    {"name": "anildash.com", "xmlUrl": "https://anildash.com/feed.xml", "htmlUrl": "https://anildash.com"},
    {"name": "aresluna.org", "xmlUrl": "https://aresluna.org/main.rss", "htmlUrl": "https://aresluna.org"},
    {"name": "michael.stapelberg.ch", "xmlUrl": "https://michael.stapelberg.ch/feed.xml", "htmlUrl": "https://michael.stapelberg.ch"},
    {"name": "miguelgrinberg.com", "xmlUrl": "https://blog.miguelgrinberg.com/feed", "htmlUrl": "https://miguelgrinberg.com"},
    {"name": "keygen.sh", "xmlUrl": "https://keygen.sh/blog/feed.xml", "htmlUrl": "https://keygen.sh"},
    {"name": "mjg59.dreamwidth.org", "xmlUrl": "https://mjg59.dreamwidth.org/data/rss", "htmlUrl": "https://mjg59.dreamwidth.org"},
    {"name": "computer.rip", "xmlUrl": "https://computer.rip/rss.xml", "htmlUrl": "https://computer.rip"},
    # {"name": "tedunangst.com", "xmlUrl": "https://www.tedunangst.com/flak/rss", "htmlUrl": "https://tedunangst.com"},
]

CATEGORY_META = {
    'ai-ml': {'emoji': '🤖', 'label': 'AI / ML'},
    'security': {'emoji': '🔒', 'label': '安全'},
    'engineering': {'emoji': '⚙️', 'label': '工程'},
    'tools': {'emoji': '🛠', 'label': '工具 / 开源'},
    'opinion': {'emoji': '💡', 'label': '观点 / 杂谈'},
    'other': {'emoji': '📝', 'label': '其他'},
}

VALID_CATEGORIES = {'ai-ml', 'security', 'engineering', 'tools', 'opinion', 'other'}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Article:
    title: str
    link: str
    pub_date: datetime
    description: str
    source_name: str
    source_url: str


@dataclass
class ScoredArticle:
    title: str
    link: str
    pub_date: datetime
    description: str
    source_name: str
    source_url: str
    score: int
    score_breakdown: Dict[str, int]
    category: str
    keywords: List[str]
    title_zh: str
    summary: str
    reason: str


# ============================================================================
# Utility Functions
# ============================================================================

def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Decode HTML entities
    text = html.unescape(text)
    # Decode numeric entities
    def decode_numeric(m):
        code = int(m.group(1))
        return chr(code)
    text = re.sub(r'&#(\d+);', decode_numeric, text)
    return text.strip()


def extract_cdata(text: str) -> str:
    """Extract content from CDATA sections."""
    match = re.search(r'<!\[CDATA\[([\s\S]*?)\]\]>', text)
    return match.group(1) if match else text


def get_tag_content(element: ET.Element, tag_name: str, namespace: str = '') -> str:
    """Get text content from an XML tag."""
    if namespace:
        tag_name = f'{{{namespace}}}{tag_name}'
    
    child = element.find(tag_name)
    if child is not None and child.text:
        return extract_cdata(child.text)
    return ''


def get_attr_value(element: ET.Element, tag_name: str, attr_name: str, namespace: str = '') -> str:
    """Get attribute value from an XML tag."""
    if namespace:
        tag_name = f'{{{namespace}}}{tag_name}'
    
    child = element.find(tag_name)
    if child is not None:
        return child.get(attr_name, '')
    return ''


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats."""
    if not date_str:
        return None
    
    # Try common formats
    formats = [
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try email.utils parsedate
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        pass
    
    return None


# ============================================================================
# RSS/Atom Parsing
# ============================================================================

def parse_feed_xml(xml_content: str, feed_info: Dict[str, str]) -> List[Article]:
    """Parse RSS or Atom feed XML and return list of articles."""
    articles = []
    
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"[AIdaily] ✗ {feed_info['name']}: XML parse error - {e}")
        return articles
    
    # Detect format: Atom vs RSS
    is_atom = root.tag.endswith('feed') or 'http://www.w3.org/2005/Atom' in root.tag
    
    # Get namespace
    namespace = ''
    if root.tag.startswith('{'):
        namespace = root.tag[1:root.tag.index('}')]
    
    if is_atom:
        # Atom format: <entry>
        entries = root.findall('entry', {'': namespace} if namespace else {})
        if not entries and namespace:
            entries = root.findall(f'{{{namespace}}}entry')
        
        for entry in entries:
            title = get_tag_content(entry, 'title', namespace)
            title = strip_html(title)
            
            # Atom link: <link href="..." rel="alternate"/>
            link = ''
            link_elems = entry.findall('link', {'': namespace} if namespace else {})
            if not link_elems and namespace:
                link_elems = entry.findall(f'{{{namespace}}}link')
            
            for link_elem in link_elems:
                rel = link_elem.get('rel', '')
                href = link_elem.get('href', '')
                if href and (rel == 'alternate' or not rel):
                    link = href
                    break
            
            pub_date_str = get_tag_content(entry, 'published', namespace) or get_tag_content(entry, 'updated', namespace)
            pub_date = parse_date(pub_date_str) or datetime.now(timezone.utc)
            
            description = get_tag_content(entry, 'summary', namespace) or get_tag_content(entry, 'content', namespace)
            description = strip_html(description)[:500]
            
            if title or link:
                articles.append(Article(
                    title=title,
                    link=link,
                    pub_date=pub_date,
                    description=description,
                    source_name=feed_info['name'],
                    source_url=feed_info['htmlUrl']
                ))
    else:
        # RSS format: <item>
        items = root.findall('item', {'': namespace} if namespace else {})
        if not items and namespace:
            items = root.findall(f'{{{namespace}}}item')
        
        for item in items:
            title = get_tag_content(item, 'title', namespace)
            title = strip_html(title)
            
            link = get_tag_content(item, 'link', namespace) or get_tag_content(item, 'guid', namespace)
            
            pub_date_str = (
                get_tag_content(item, 'pubDate', namespace) or
                get_tag_content(item, 'dc:date', namespace) or
                get_tag_content(item, 'date', namespace)
            )
            pub_date = parse_date(pub_date_str) or datetime.now(timezone.utc)
            
            # Try content:encoded first, then description
            description = ''
            if namespace:
                content_elem = item.find(f'{{{namespace}}}content')
                if content_elem is not None and content_elem.text:
                    description = content_elem.text
            description = description or get_tag_content(item, 'description', namespace)
            description = strip_html(description)[:500]
            
            if title or link:
                articles.append(Article(
                    title=title,
                    link=link,
                    pub_date=pub_date,
                    description=description,
                    source_name=feed_info['name'],
                    source_url=feed_info['htmlUrl']
                ))
    
    return articles


# ============================================================================
# Feed Fetching
# ============================================================================

def fetch_feed(feed: Dict[str, str]) -> List[Article]:
    """Fetch a single RSS feed and return articles."""
    try:
        request = urllib.request.Request(
            feed['xmlUrl'],
            headers={
                'User-Agent': 'AI-Daily-Digest/1.0 (RSS Reader)',
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
            }
        )
        
        # Create SSL context that doesn't verify certificates (for compatibility)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=FEED_FETCH_TIMEOUT, context=ssl_context) as response:
            if response.status != 200:
                raise urllib.error.HTTPError(feed['xmlUrl'], response.status, f"HTTP {response.status}", {}, None)
            
            xml_content = response.read().decode('utf-8', errors='ignore')
            return parse_feed_xml(xml_content, feed)
    
    except urllib.error.HTTPError as e:
        print(f"[AIdaily] ✗ {feed['name']}: HTTP {e.code}")
    except urllib.error.URLError as e:
        if 'timeout' in str(e).lower() or 'timed out' in str(e).lower():
            print(f"[AIdaily] ✗ {feed['name']}: timeout")
        else:
            print(f"[AIdaily] ✗ {feed['name']}: {e.reason}")
    except Exception as e:
        print(f"[AIdaily] ✗ {feed['name']}: {e}")
    
    return []


def fetch_all_feeds(feeds: List[Dict[str, str]]) -> Tuple[List[Article], int, int]:
    """Fetch all feeds concurrently."""
    all_articles = []
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=FEED_CONCURRENCY) as executor:
        futures = {executor.submit(fetch_feed, feed): feed for feed in feeds}
        
        for i, future in enumerate(as_completed(futures), 1):
            articles = future.result()
            if articles:
                all_articles.extend(articles)
                success_count += 1
            else:
                fail_count += 1
            
            if i % 10 == 0 or i == len(feeds):
                print(f"[AIdaily] Progress: {i}/{len(feeds)} feeds processed ({success_count} ok, {fail_count} failed)")
    
    print(f"[AIdaily] Fetched {len(all_articles)} articles from {success_count} feeds ({fail_count} failed)")
    return all_articles, success_count, fail_count


# ============================================================================
# AI Providers
# ============================================================================

class AIClient:
    """Base class for AI clients."""
    
    async def call(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIAIClient(AIClient):
    """OpenAI-compatible API client."""
    
    def __init__(self, api_key: str, api_base: str, model: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.model = model
    
    async def call(self, prompt: str) -> str:
        import aiohttp
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "top_p": 0.8,
        }
        
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error ({response.status}): {error_text}")
                
                data = await response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Handle both string and array content formats
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    return '\n'.join(item.get('text', '') for item in content if item.get('type') == 'text')
                return ''


class AIClientWrapper(AIClient):
    """OpenAI-compatible API client wrapper."""

    def __init__(
        self,
        openai_api_key: str,
        openai_api_base: str = OPENAI_DEFAULT_API_BASE,
        openai_model: str = OPENAI_DEFAULT_MODEL,
    ):
        self.openai_client = OpenAIAIClient(openai_api_key, openai_api_base, openai_model)

    async def call(self, prompt: str) -> str:
        return await self.openai_client.call(prompt)


def parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from AI response, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown code blocks
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return json.loads(text)


# ============================================================================
# AI Scoring
# ============================================================================

def build_scoring_prompt(articles: List[Dict[str, Any]]) -> str:
    """Build prompt for AI scoring."""
    articles_list = '\n\n---\n\n'.join([
        f"Index {a['index']}: [{a['sourceName']}] {a['title']}\n{a['description'][:300]}"
        for a in articles
    ])
    
    return f"""你是一个技术内容策展人，正在为一份面向技术爱好者的每日精选摘要筛选文章。

请对以下文章进行三个维度的评分（1-10 整数，10 分最高），并为每篇文章分配一个分类标签和提取 2-4 个关键词。

## 评分维度

### 1. 相关性 (relevance) - 对技术/编程/AI/互联网从业者的价值
- 10: 所有技术人都应该知道的重大事件/突破
- 7-9: 对大部分技术从业者有价值
- 4-6: 对特定技术领域有价值
- 1-3: 与技术行业关联不大

### 2. 质量 (quality) - 文章本身的深度和写作质量
- 10: 深度分析，原创洞见，引用丰富
- 7-9: 有深度，观点独到
- 4-6: 信息准确，表达清晰
- 1-3: 浅尝辄止或纯转述

### 3. 时效性 (timeliness) - 当前是否值得阅读
- 10: 正在发生的重大事件/刚发布的重要工具
- 7-9: 近期热点相关
- 4-6: 常青内容，不过时
- 1-3: 过时或无时效价值

## 分类标签（必须从以下选一个）
- ai-ml: AI、机器学习、LLM、深度学习相关
- security: 安全、隐私、漏洞、加密相关
- engineering: 软件工程、架构、编程语言、系统设计
- tools: 开发工具、开源项目、新发布的库/框架
- opinion: 行业观点、个人思考、职业发展、文化评论
- other: 以上都不太适合的

## 关键词提取
提取 2-4 个最能代表文章主题的关键词（用英文，简短，如 "Rust", "LLM", "database", "performance"）

## 待评分文章

{articles_list}

请严格按 JSON 格式返回，不要包含 markdown 代码块或其他文字：
{{
  "results": [
    {{
      "index": 0,
      "relevance": 8,
      "quality": 7,
      "timeliness": 9,
      "category": "engineering",
      "keywords": ["Rust", "compiler", "performance"]
    }}
  ]
}}"""


async def score_articles_with_ai(
    articles: List[Article],
    ai_client: AIClient
) -> Dict[int, Dict[str, Any]]:
    """Score articles using AI."""
    all_scores = {}
    
    indexed = [
        {
            'index': i,
            'title': a.title,
            'description': a.description,
            'sourceName': a.source_name,
        }
        for i, a in enumerate(articles)
    ]
    
    batches = [indexed[i:i + BATCH_SIZE] for i in range(0, len(indexed), BATCH_SIZE)]
    
    print(f"[AIdaily] AI scoring: {len(articles)} articles in {len(batches)} batches")
    
    for i in range(0, len(batches), MAX_CONCURRENT_REQUESTS):
        batch_group = batches[i:i + MAX_CONCURRENT_REQUESTS]
        
        tasks = []
        for batch in batch_group:
            async def score_batch(batch=batch):
                try:
                    prompt = build_scoring_prompt(batch)
                    response_text = await ai_client.call(prompt)
                    parsed = parse_json_response(response_text)
                    
                    results = {}
                    if 'results' in parsed and isinstance(parsed['results'], list):
                        for result in parsed['results']:
                            idx = result.get('index')
                            if idx is not None:
                                clamp = lambda v: min(10, max(1, int(v)))
                                cat = result.get('category', 'other')
                                if cat not in VALID_CATEGORIES:
                                    cat = 'other'
                                results[idx] = {
                                    'relevance': clamp(result.get('relevance', 5)),
                                    'quality': clamp(result.get('quality', 5)),
                                    'timeliness': clamp(result.get('timeliness', 5)),
                                    'category': cat,
                                    'keywords': result.get('keywords', [])[:4] if isinstance(result.get('keywords'), list) else [],
                                }
                    return results
                except Exception as e:
                    print(f"[AIdaily] Scoring batch failed: {e}")
                    # Return default scores
                    return {item['index']: {'relevance': 5, 'quality': 5, 'timeliness': 5, 'category': 'other', 'keywords': []} for item in batch}
            
            tasks.append(score_batch())
        
        batch_results = await asyncio.gather(*tasks)
        for results in batch_results:
            all_scores.update(results)
        
        print(f"[AIdaily] Scoring progress: {min(i + MAX_CONCURRENT_REQUESTS, len(batches))}/{len(batches)} batches")
    
    return all_scores


# ============================================================================
# AI Summarization
# ============================================================================

def build_summary_prompt(articles: List[Dict[str, Any]], lang: str) -> str:
    """Build prompt for AI summarization."""
    articles_list = '\n\n---\n\n'.join([
        f"Index {a['index']}: [{a['sourceName']}] {a['title']}\nURL: {a['link']}\n{a['description'][:800]}"
        for a in articles
    ])
    
    lang_instruction = (
        '请用中文撰写摘要和推荐理由。如果原文是英文，请翻译为中文。标题翻译也用中文。'
        if lang == 'zh'
        else 'Write summaries, reasons, and title translations in English.'
    )
    
    return f"""你是一个技术内容摘要专家。请为以下文章完成三件事：

1. **中文标题** (titleZh): 将英文标题翻译成自然的中文。如果原标题已经是中文则保持不变。
2. **摘要** (summary): 4-6 句话的结构化摘要，让读者不点进原文也能了解核心内容。包含：
   - 文章讨论的核心问题或主题（1 句）
   - 关键论点、技术方案或发现（2-3 句）
   - 结论或作者的核心观点（1 句）
3. **推荐理由** (reason): 1 句话说明"为什么值得读"，区别于摘要（摘要说"是什么"，推荐理由说"为什么"）。

{lang_instruction}

摘要要求：
- 直接说重点，不要用"本文讨论了..."、"这篇文章介绍了..."这种开头
- 包含具体的技术名词、数据、方案名称或观点
- 保留关键数字和指标（如性能提升百分比、用户数、版本号等）
- 如果文章涉及对比或选型，要点出比较对象和结论
- 目标：读者花 30 秒读完摘要，就能决定是否值得花 10 分钟读原文

## 待摘要文章

{articles_list}

请严格按 JSON 格式返回：
{{
  "results": [
    {{
      "index": 0,
      "titleZh": "中文翻译的标题",
      "summary": "摘要内容...",
      "reason": "推荐理由..."
    }}
  ]
}}"""


async def summarize_articles(
    articles: List[Article],
    ai_client: AIClient,
    lang: str
) -> Dict[int, Dict[str, str]]:
    """Generate summaries for articles using AI."""
    summaries = {}
    
    indexed = [
        {
            'index': i,
            'title': a.title,
            'description': a.description,
            'sourceName': a.source_name,
            'link': a.link,
        }
        for i, a in enumerate(articles)
    ]
    
    batches = [indexed[i:i + BATCH_SIZE] for i in range(0, len(indexed), BATCH_SIZE)]
    
    print(f"[AIdaily] Generating summaries for {len(articles)} articles in {len(batches)} batches")
    
    for i in range(0, len(batches), MAX_CONCURRENT_REQUESTS):
        batch_group = batches[i:i + MAX_CONCURRENT_REQUESTS]
        
        tasks = []
        for batch in batch_group:
            async def summarize_batch(batch=batch):
                try:
                    prompt = build_summary_prompt(batch, lang)
                    response_text = await ai_client.call(prompt)
                    parsed = parse_json_response(response_text)
                    
                    results = {}
                    if 'results' in parsed and isinstance(parsed['results'], list):
                        for result in parsed['results']:
                            idx = result.get('index')
                            if idx is not None:
                                results[idx] = {
                                    'titleZh': result.get('titleZh', ''),
                                    'summary': result.get('summary', ''),
                                    'reason': result.get('reason', ''),
                                }
                    return results
                except Exception as e:
                    print(f"[AIdaily] Summary batch failed: {e}")
                    # Return fallback summaries
                    return {item['index']: {'titleZh': item['title'], 'summary': item['title'], 'reason': ''} for item in batch}
            
            tasks.append(summarize_batch())
        
        batch_results = await asyncio.gather(*tasks)
        for results in batch_results:
            summaries.update(results)
        
        print(f"[AIdaily] Summary progress: {min(i + MAX_CONCURRENT_REQUESTS, len(batches))}/{len(batches)} batches")
    
    return summaries


# ============================================================================
# AI Highlights
# ============================================================================

async def generate_highlights(
    articles: List[ScoredArticle],
    ai_client: AIClient,
    lang: str
) -> str:
    """Generate today's highlights summary."""
    article_list = '\n'.join([
        f"{i+1}. [{a.category}] {a.title_zh or a.title} — {a.summary[:100]}"
        for i, a in enumerate(articles[:10])
    ])
    
    lang_note = '用中文回答。' if lang == 'zh' else 'Write in English.'
    
    prompt = f"""根据以下今日精选技术文章列表，写一段 3-5 句话的"今日看点"总结。
要求：
- 提炼出今天技术圈的 2-3 个主要趋势或话题
- 不要逐篇列举，要做宏观归纳
- 风格简洁有力，像新闻导语
{lang_note}

文章列表：
{article_list}

直接返回纯文本总结，不要 JSON，不要 markdown 格式。"""
    
    try:
        text = await ai_client.call(prompt)
        return text.strip()
    except Exception as e:
        print(f"[AIdaily] Highlights generation failed: {e}")
        return ''


# ============================================================================
# Visualization Helpers
# ============================================================================

def humanize_time(pub_date: datetime) -> str:
    """Convert datetime to human-readable relative time."""
    now = datetime.now(timezone.utc)
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    
    diff = now - pub_date
    diff_mins = int(diff.total_seconds() / 60)
    diff_hours = diff_mins // 60
    diff_days = diff_hours // 24
    
    if diff_mins < 60:
        return f"{diff_mins} 分钟前"
    elif diff_hours < 24:
        return f"{diff_hours} 小时前"
    elif diff_days < 7:
        return f"{diff_days} 天前"
    else:
        return pub_date.strftime('%Y-%m-%d')


def generate_keyword_bar_chart(articles: List[ScoredArticle]) -> str:
    """Generate Mermaid bar chart for keywords."""
    kw_count = Counter()
    for a in articles:
        for kw in a.keywords:
            kw_count[kw.lower()] += 1
    
    sorted_kws = kw_count.most_common(12)
    
    if not sorted_kws:
        return ''
    
    labels = ', '.join([f'"{kw}"' for kw, _ in sorted_kws])
    values = ', '.join([str(count) for _, count in sorted_kws])
    max_val = sorted_kws[0][1]
    
    chart = '```mermaid\n'
    chart += 'xychart-beta horizontal\n'
    chart += f'    title "高频关键词"\n'
    chart += f'    x-axis [{labels}]\n'
    chart += f'    y-axis "出现次数" 0 --> {max_val + 2}\n'
    chart += f'    bar [{values}]\n'
    chart += '```\n'
    
    return chart


def generate_category_pie_chart(articles: List[ScoredArticle]) -> str:
    """Generate Mermaid pie chart for categories."""
    cat_count = Counter(a.category for a in articles)
    
    if not cat_count:
        return ''
    
    chart = '```mermaid\n'
    chart += 'pie showData\n'
    chart += '    title "文章分类分布"\n'
    for cat, count in cat_count.most_common():
        meta = CATEGORY_META.get(cat, CATEGORY_META['other'])
        chart += f'    "{meta["emoji"]} {meta["label"]}" : {count}\n'
    chart += '```\n'
    
    return chart


def generate_ascii_bar_chart(articles: List[ScoredArticle]) -> str:
    """Generate ASCII bar chart for keywords."""
    kw_count = Counter()
    for a in articles:
        for kw in a.keywords:
            kw_count[kw.lower()] += 1
    
    sorted_kws = kw_count.most_common(10)
    
    if not sorted_kws:
        return ''
    
    max_val = sorted_kws[0][1]
    max_bar_width = 20
    max_label_len = max(len(kw) for kw, _ in sorted_kws)
    
    chart = '```\n'
    for label, value in sorted_kws:
        bar_len = max(1, round((value / max_val) * max_bar_width))
        bar = '█' * bar_len + '░' * (max_bar_width - bar_len)
        chart += f'{label.ljust(max_label_len)} │ {bar} {value}\n'
    chart += '```\n'
    
    return chart


def generate_tag_cloud(articles: List[ScoredArticle]) -> str:
    """Generate tag cloud from keywords."""
    kw_count = Counter()
    for a in articles:
        for kw in a.keywords:
            kw_count[kw.lower()] += 1
    
    sorted_kws = kw_count.most_common(20)
    
    if not sorted_kws:
        return ''
    
    tags = []
    for i, (word, count) in enumerate(sorted_kws):
        if i < 3:
            tags.append(f'**{word}**({count})')
        else:
            tags.append(f'{word}({count})')
    
    return ' · '.join(tags)


# ============================================================================
# Report Generation
# ============================================================================

def generate_digest_report(
    articles: List[ScoredArticle],
    highlights: str,
    stats: Dict[str, Any]
) -> str:
    """Generate the final digest report in Markdown."""
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    report = f"# 📰 AI 博客每日精选 — {date_str}\n\n"
    report += f"> 来自 Karpathy 推荐的 {stats['totalFeeds']} 个顶级技术博客，AI 精选 Top {len(articles)}\n\n"
    
    # Today's Highlights
    if highlights:
        report += "## 📝 今日看点\n\n"
        report += f"{highlights}\n\n"
        report += "---\n\n"
    
    # Top 3 Deep Showcase
    if len(articles) >= 3:
        report += "## 🏆 今日必读\n\n"
        medals = ['🥇', '🥈', '🥉']
        
        for i in range(min(3, len(articles))):
            a = articles[i]
            cat_meta = CATEGORY_META.get(a.category, CATEGORY_META['other'])
            
            report += f"{medals[i]} **{a.title_zh or a.title}**\n\n"
            report += f"[{a.title}]({a.link}) — {a.source_name} · {humanize_time(a.pub_date)} · {cat_meta['emoji']} {cat_meta['label']}\n\n"
            report += f"> {a.summary}\n\n"
            
            if a.reason:
                report += f"💡 **为什么值得读**: {a.reason}\n\n"
            
            if a.keywords:
                report += f"🏷️ {', '.join(a.keywords)}\n\n"
        
        report += "---\n\n"
    
    # Visual Statistics
    """
    report += "## 📊 数据概览\n\n"
    
    report += "| 扫描源 | 抓取文章 | 时间范围 | 精选 |\n"
    report += "|:---:|:---:|:---:|:---:|\n"
    report += f"| {stats['successFeeds']}/{stats['totalFeeds']} | {stats['totalArticles']} 篇 → {stats['filteredArticles']} 篇 | {stats['hours']}h | **{len(articles)} 篇** |\n\n"
    
    pie_chart = generate_category_pie_chart(articles)
    if pie_chart:
        report += "### 分类分布\n\n" + pie_chart
    
    bar_chart = generate_keyword_bar_chart(articles)
    if bar_chart:
        report += "### 高频关键词\n\n" + bar_chart
    
    ascii_chart = generate_ascii_bar_chart(articles)
    if ascii_chart:
        report += "<details>\n<summary>📈 纯文本关键词图（终端友好）</summary>\n\n" + ascii_chart + "</details>\n\n"
    
    tag_cloud = generate_tag_cloud(articles)
    if tag_cloud:
        report += "### 🏷️ 话题标签\n\n" + tag_cloud + "\n\n"
    
    report += "---\n\n"
    """
    # Category-Grouped Articles
    cat_groups = {}
    for a in articles:
        if a.category not in cat_groups:
            cat_groups[a.category] = []
        cat_groups[a.category].append(a)
    
    sorted_cats = sorted(cat_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    global_index = 0
    for cat_id, cat_articles in sorted_cats:
        cat_meta = CATEGORY_META.get(cat_id, CATEGORY_META['other'])
        report += f"## {cat_meta['emoji']} {cat_meta['label']}\n\n"
        
        for a in cat_articles:
            global_index += 1
            score_total = a.score_breakdown['relevance'] + a.score_breakdown['quality'] + a.score_breakdown['timeliness']
            
            report += f"### {global_index}. {a.title_zh or a.title}\n\n"
            report += f"[{a.title}]({a.link}) — **{a.source_name}** · {humanize_time(a.pub_date)} · ⭐ {score_total}/30\n\n"
            report += f"> {a.summary}\n\n"
            
            if a.keywords:
                report += f"🏷️ {', '.join(a.keywords)}\n\n"
            
            report += "---\n\n"
    
    # Footer
    # time_str = now.strftime('%H:%M')
    # report += f"*生成于 {date_str} {time_str} | 扫描 {stats['successFeeds']} 源 → 获取 {stats['totalArticles']} 篇 → 精选 {len(articles)} 篇*\n"
    # report += f"*生成于 {date_str} {time_str} *\n"
    report += "*由「AIGC之路」制作，欢迎关注同名微信公众号 💡*\n"
    
    return report


# ============================================================================
# Main
# ============================================================================

async def main_async(args: argparse.Namespace):
    """Main async function."""
    # Get API keys
    openai_api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    openai_api_base = os.environ.get('OPENAI_API_BASE', OPENAI_DEFAULT_API_BASE).strip()
    openai_model = os.environ.get('OPENAI_MODEL', '').strip()

    if not openai_api_key:
        print('[AIdaily] Error: Missing API key. Set OPENAI_API_KEY.')
        sys.exit(1)

    # Infer model if not specified
    if not openai_model:
        if 'deepseek' in openai_api_base.lower():
            openai_model = 'deepseek-chat'
        else:
            openai_model = OPENAI_DEFAULT_MODEL

    # Create AI client
    ai_client = AIClientWrapper(
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base,
        openai_model=openai_model,
    )

    # Determine output path
    output_path = args.output or f"./digest-{datetime.now().strftime('%Y%m%d')}.md"

    print('[AIdaily] === AI Daily Digest ===')
    print(f'[AIdaily] Time range: {args.hours} hours')
    print(f'[AIdaily] Top N: {args.top_n}')
    print(f'[AIdaily] Language: {args.lang}')
    print(f'[AIdaily] Output: {output_path}')
    print(f'[AIdaily] AI provider: {openai_api_base} (model={openai_model})')
    print('')
    
    # Step 1: Fetch feeds
    print(f'[AIdaily] Step 1/5: Fetching {len(RSS_FEEDS)} RSS feeds...')
    all_articles, success_count, fail_count = fetch_all_feeds(RSS_FEEDS)
    
    if not all_articles:
        print('[AIdaily] Error: No articles fetched from any feed. Check network connection.')
        sys.exit(1)
    
    # Step 2: Filter by time
    print(f'[AIdaily] Step 2/5: Filtering by time range ({args.hours} hours)...')
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    recent_articles = [a for a in all_articles if a.pub_date.replace(tzinfo=timezone.utc) > cutoff_time]
    
    print(f'[AIdaily] Found {len(recent_articles)} articles within last {args.hours} hours')
    
    if not recent_articles:
        print(f'[AIdaily] Error: No articles found within the last {args.hours} hours.')
        print('[AIdaily] Try increasing --hours (e.g., --hours 168 for one week)')
        sys.exit(1)
    
    # Step 3: Score articles
    print(f'[AIdaily] Step 3/5: AI scoring {len(recent_articles)} articles...')
    scores = await score_articles_with_ai(recent_articles, ai_client)
    
    scored_articles = []
    for i, article in enumerate(recent_articles):
        score_data = scores.get(i, {
            'relevance': 5,
            'quality': 5,
            'timeliness': 5,
            'category': 'other',
            'keywords': [],
        })
        total_score = score_data['relevance'] + score_data['quality'] + score_data['timeliness']
        scored_articles.append({
            'article': article,
            'total_score': total_score,
            'score_data': score_data,
        })
    
    scored_articles.sort(key=lambda x: x['total_score'], reverse=True)
    top_articles_data = scored_articles[:args.top_n]
    
    score_range = f"{top_articles_data[-1]['total_score'] if top_articles_data else 0} - {top_articles_data[0]['total_score'] if top_articles_data else 0}"
    print(f'[AIdaily] Top {args.top_n} articles selected (score range: {score_range})')
    
    # Step 4: Generate summaries
    print('[AIdaily] Step 4/5: Generating AI summaries...')
    top_articles = [item['article'] for item in top_articles_data]
    summaries = await summarize_articles(top_articles, ai_client, args.lang)
    
    final_articles = []
    for i, item in enumerate(top_articles_data):
        article = item['article']
        score_data = item['score_data']
        sm = summaries.get(i, {
            'titleZh': article.title,
            'summary': article.description[:200],
            'reason': '',
        })
        
        final_articles.append(ScoredArticle(
            title=article.title,
            link=article.link,
            pub_date=article.pub_date,
            description=article.description,
            source_name=article.source_name,
            source_url=article.source_url,
            score=item['total_score'],
            score_breakdown={
                'relevance': score_data['relevance'],
                'quality': score_data['quality'],
                'timeliness': score_data['timeliness'],
            },
            category=score_data['category'],
            keywords=score_data['keywords'],
            title_zh=sm['titleZh'],
            summary=sm['summary'],
            reason=sm['reason'],
        ))
    
    # Step 5: Generate highlights
    print('[AIdaily] Step 5/5: Generating today\'s highlights...')
    highlights = await generate_highlights(final_articles, ai_client, args.lang)
    
    # Generate report
    successful_sources = len(set(a.source_name for a in all_articles))
    
    report = generate_digest_report(final_articles, highlights, {
        'totalFeeds': len(RSS_FEEDS),
        'successFeeds': successful_sources,
        'totalArticles': len(all_articles),
        'filteredArticles': len(recent_articles),
        'hours': args.hours,
        'lang': args.lang,
    })
    
    # Write output
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding='utf-8')
    
    print('')
    print('[AIdaily] ✅ Done!')
    print(f'[AIdaily] 📁 Report: {output_path}')
    print(f'[AIdaily] 📊 Stats: {successful_sources} sources → {len(all_articles)} articles → {len(recent_articles)} recent → {len(final_articles)} selected')
    
    if final_articles:
        print('')
        print('[AIdaily] 🏆 Top 3 Preview:')
        for i, a in enumerate(final_articles[:3]):
            print(f"  {i+1}. {a.title_zh or a.title}")
            print(f"     {a.summary[:80]}...")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AI Daily - AI-powered RSS from 90 top tech blogs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_daily.py --hours 24 --top-n 10 --lang zh
  python ai_daily.py --hours 72 --top-n 20 --lang en --output ./my-digest.md

Environment:
  OPENAI_API_KEY   Required. API key for OpenAI-compatible APIs
  OPENAI_API_BASE  Optional base URL (default: https://open.bigmodel.cn/api/paas/v4/)
  OPENAI_MODEL     Optional model name (default: glm-4.7, or deepseek-chat for DeepSeek base)
        """
    )
    
    parser.add_argument('--hours', type=int, default=24, help='Time range in hours (default: 24)')
    parser.add_argument('--top-n', type=int, default=15, help='Number of top articles to include (default: 15)')
    parser.add_argument('--lang', choices=['zh', 'en'], default='zh', help='Summary language: zh or en (default: zh)')
    parser.add_argument('--output', '-o', type=str, default='', help='Output file path (default: ./ai-daily-YYYYMMDD.md)')
    
    args = parser.parse_args()
    
    # Run async main
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
