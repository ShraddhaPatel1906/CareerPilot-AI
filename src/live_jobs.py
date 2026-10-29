"""Real recent job discovery from public board APIs.

Only jobs with a *known published/created date* are shown. Updated timestamps
are not treated as publication dates. Public job data is cached (not resumes).
Applications always open the employer's original job page; we never claim to
submit forms or send messages on the user's behalf.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import os
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from src.interview_service import SKILL_NAMES

SOURCE_CACHE_SECONDS = 600
_SOURCE_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
SOURCE_LIMIT = 900
HEADERS = {"User-Agent": "CareerPilotAI/1.0 (Public job API reader)"}
ROLE_WORDS = {"ai", "ml", "data", "scientist", "science", "analyst", "analytics", "engineer", "developer", "software", "machine", "learning", "generative", "nlp", "backend", "frontend", "full", "stack", "intern", "internship", "research", "business", "product", "devops", "cloud", "python", "sql"}
STOP_WORDS = {"and", "or", "the", "for", "with", "of", "senior", "junior", "associate", "entry", "level", "remote", "a", "an", "role", "position", "you", "are", "applying"}
EMAIL_RE = re.compile(r'\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b', re.I)


class _StripHTML(HTMLParser):
    """Extract readable, line-separated text from untrusted job-board HTML."""
    BLOCK_TAGS = {'p', 'div', 'section', 'article', 'header', 'footer', 'br',
                  'ul', 'ol', 'li', 'tr', 'blockquote', 'hr',
                  'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    IGNORE_TAGS = {'script', 'style', 'noscript', 'svg', 'iframe'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignore_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in self.IGNORE_TAGS:
            self.ignore_depth += 1
        elif not self.ignore_depth:
            if tag in self.BLOCK_TAGS:
                self.parts.append('\n')
            if tag == 'li':
                self.parts.append('• ')

    def handle_startendtag(self, tag: str, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str):
        if tag in self.IGNORE_TAGS:
            self.ignore_depth = max(0, self.ignore_depth - 1)
        elif not self.ignore_depth and tag in self.BLOCK_TAGS:
            self.parts.append('\n')

    def handle_data(self, data: str):
        if not self.ignore_depth:
            self.parts.append(data)


def to_text(value: Any, length: int = 7000) -> str:
    """Decode nested HTML entities and retain headings/paragraph/list boundaries.

    Job boards may send markup as both HTML and strings like
    ``&amp;lt;h3&amp;gt;About us&amp;lt;/h3&amp;gt;``.  This never exposes
    that HTML to the browser: the output is strictly plain text.
    """
    raw = str(value or '')[:30000]
    for _ in range(3):
        decoded = html.unescape(raw)
        if decoded == raw:
            break
        raw = decoded
    parser = _StripHTML()
    parser.feed(raw)
    parser.close()
    lines = [re.sub(r'[ \t\f\v]+', ' ', line).strip()
             for line in ''.join(parser.parts).replace('\r', '\n').split('\n')]
    readable = '\n'.join(line for line in lines if line)
    return readable[:length]


def published_datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        value = float(value)
        if value > 10**12:
            value /= 1000
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
            return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def safe_url(url: Any) -> str | None:
    if not isinstance(url, str) or len(url) > 2000:
        return None
    try:
        parts = urlparse(url.strip())
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
            return None
        if parts.hostname in {'localhost', '127.0.0.1', '0.0.0.0'}:
            return None
    except ValueError:
        return None
    return url.strip()


def employer_apply_email(description: str) -> str | None:
    # Only show an email when text explicitly calls for applications there.
    for match in EMAIL_RE.finditer(description):
        context = description[max(0, match.start() - 130):match.start()].lower()
        if re.search(r'(apply\s*(?:via|at|to|by|through)|send\s+(?:your\s+)?(?:cv|resume|application)|email\s+(?:your\s+)?(?:cv|resume|application)|applications?\s+(?:to|at))', context):
            return match.group(0)
    return None


def normalize_job(*, source: str, external_id: str, title: Any, company: Any,
                  location: Any, url: Any, posted: Any, description: Any,
                  remote: bool = False) -> dict[str, Any] | None:
    link = safe_url(url)
    created = published_datetime(posted)
    name = to_text(title, 180)
    org = to_text(company, 150)
    if not link or not created or not name or not org:
        return None
    desc = to_text(description, 7000)
    return {
        'id': hashlib.sha256((source + ':' + str(external_id) + ':' + link).encode()).hexdigest()[:18],
        'title': name, 'company': org, 'location': to_text(location, 140) or ('Remote' if remote else 'Unspecified'),
        'url': link, 'posted_at': created.isoformat(), 'source': source,
        'description': desc[:5500], '_full_description': desc,
        'remote': bool(remote) or bool(re.search(r'\bremote\b', str(location), re.I)),
        'email_to_apply': employer_apply_email(desc),
    }


def parse_remotive(payload: dict) -> list[dict]:
    result = []
    for item in payload.get('jobs', [])[:SOURCE_LIMIT]:
        if not isinstance(item, dict):
            continue
        job = normalize_job(source='Remotive', external_id=str(item.get('id','')),
            title=item.get('title'), company=item.get('company_name'),
            location=item.get('candidate_required_location') or 'Remote — see eligibility',
            url=item.get('url'), posted=item.get('publication_date'),
            description=item.get('description'), remote=True)
        if job: result.append(job)
    return result


def parse_arbeitnow(payload: dict) -> list[dict]:
    result = []
    for item in payload.get('data', [])[:SOURCE_LIMIT]:
        if not isinstance(item, dict): continue
        job = normalize_job(source='Arbeitnow', external_id=str(item.get('slug','')),
            title=item.get('title'), company=item.get('company_name'),
            location=item.get('location'), url=item.get('url'),
            posted=item.get('created_at'), description=item.get('description'),
            remote=bool(item.get('remote')))
        if job: result.append(job)
    return result




def parse_jobicy(payload: dict) -> list[dict]:
    result=[]
    for item in payload.get('jobs', [])[:SOURCE_LIMIT]:
        if not isinstance(item, dict): continue
        job = normalize_job(source='Jobicy', external_id=str(item.get('id','')),
            title=item.get('jobTitle'), company=item.get('companyName'),
            location=item.get('jobGeo') or 'Remote — check location restrictions',
            url=item.get('url'), posted=item.get('pubDate'),
            description=item.get('jobDescription') or item.get('jobExcerpt'), remote=True)
        if job: result.append(job)
    return result

def parse_lever(payload: list, board: str) -> list[dict]:
    result=[]
    for item in payload[:SOURCE_LIMIT]:
        if not isinstance(item, dict): continue
        categories = item.get('categories') or {}
        desc = item.get('descriptionPlain') or ' '.join(x.get('content', '') for x in item.get('lists', []) if isinstance(x, dict))
        job = normalize_job(source=f'Lever/{board}', external_id=str(item.get('id','')),
            title=item.get('text'), company=board, location=categories.get('location'),
            url=item.get('hostedUrl') or item.get('applyUrl'), posted=item.get('createdAt'),
            description=desc, remote=categories.get('commitment', '').lower() == 'remote')
        if job: result.append(job)
    return result


def parse_greenhouse(payload: dict, board: str) -> list[dict]:
    result=[]
    for item in payload.get('jobs', [])[:SOURCE_LIMIT]:
        if not isinstance(item, dict): continue
        # updated_at != first_published. No trustworthy publication date = skip.
        posted = item.get('first_published') or item.get('published_at')
        job = normalize_job(source=f'Greenhouse/{board}', external_id=str(item.get('id','')),
            title=item.get('title'), company=board,
            location=(item.get('location') or {}).get('name'), url=item.get('absolute_url'),
            posted=posted, description=item.get('content'))
        if job: result.append(job)
    return result


def source_specs() -> list[tuple[str, str, str, str]]:
    result = [
        ('remotive', 'https://remotive.com/api/remote-jobs?limit=500', 'remotive', ''),
        ('arbeitnow', 'https://www.arbeitnow.com/api/job-board-api', 'arbeitnow', ''),
        ('jobicy', 'https://jobicy.com/api/v2/remote-jobs?count=50', 'jobicy', ''),
    ]
    for name, api in [('lever', 'https://api.lever.co/v0/postings/{board}?mode=json'),
                      ('greenhouse', 'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')]:
        boards = os.getenv('CAREERPILOT_' + name.upper() + '_BOARDS', '').split(',')
        for board in boards[:12]:
            board = board.strip().lower()
            if re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,60}', board):
                result.append((f'{name}/{board}', api.format(board=board), name, board))
    return result


async def load_public_jobs() -> tuple[list[dict], list[str], list[str]]:
    """Return listings, successful sources and failing sources. No resume retained."""
    sources = source_specs()
    async with httpx.AsyncClient(timeout=httpx.Timeout(11.0), follow_redirects=False, headers=HEADERS) as client:
        async def read_one(key: str, url: str, kind: str, board: str):
            cached = _SOURCE_CACHE.get(key)
            if cached and time.monotonic() - cached[0] < SOURCE_CACHE_SECONDS:
                return key, cached[1], None
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                parsed = (parse_remotive(data) if kind == 'remotive' else
                          parse_arbeitnow(data) if kind == 'arbeitnow' else
                          parse_jobicy(data) if kind == 'jobicy' else
                          parse_lever(data, board) if kind == 'lever' else
                          parse_greenhouse(data, board))
                _SOURCE_CACHE[key] = (time.monotonic(), parsed)
                return key, parsed, None
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as err:
                return key, [], err.__class__.__name__
        outcomes = await asyncio.gather(*(read_one(*s) for s in sources))
    jobs, ok, failures = [], [], []
    for key, items, err in outcomes:
        if err:
            failures.append(f'{key}: {err}')
        else:
            ok.append(key)
            jobs.extend(items)
    return jobs, ok, failures


def required_skills(text: str) -> list[str]:
    names=[]
    for s in SKILL_NAMES:
        if re.search(r'(?i)(?<![a-z0-9])' + re.escape(s) + r'(?![a-z0-9])', text):
            names.append(s)
    return names[:25]


def match_job(job: dict, candidate: dict) -> dict:
    title = job['title'].lower()
    role = str(candidate.get('role') or 'Data Scientist').lower()
    skills = [str(s).strip() for s in candidate.get('skills', [])[:35] if str(s).strip()]
    job_skills = required_skills(job['_full_description'] + ' ' + job['title'])
    candidate_set = {s.casefold() for s in skills}
    matched = [s for s in job_skills if s.casefold() in candidate_set]
    role_tokens = ({t for t in re.findall(r'[a-z]+', role) if t in ROLE_WORDS} - STOP_WORDS)
    title_tokens = set(re.findall(r'[a-z]+', title))
    relevant = bool(role_tokens & title_tokens)
    # Common adjacent job families: AI/Data profiles can match related analytics/ML positions.
    if {'ai','ml','data','science','scientist','machine','learning','analytics'} & role_tokens:
        relevant |= bool({'ai','ml','data','scientist','analytics','machine','learning','nlp'} & title_tokens)
    if 'intern' in title_tokens or 'internship' in title_tokens:
        relevant |= bool(role_tokens & title_tokens)
    skill_fraction = len(matched) / max(len(job_skills), 1)
    score = min(100, round((38 if relevant else 0) + 62 * skill_fraction))
    # Resume-relevance match only; never claim real employer shortlisting probability.
    return {'match_score': score, 'matched_skills': matched, 'required_skills': job_skills,
            'role_match': relevant}


def query_jobs(all_jobs: list[dict], candidate: dict, days: int = 3, location: str = 'all',
               now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    seen: set[str] = set()
    output: list[dict] = []
    for job in all_jobs:
        date = published_datetime(job.get('posted_at'))
        if not date or date < cutoff or date > now + timedelta(minutes=10):
            continue
        if location == 'remote' and not job.get('remote'):
            continue
        if location == 'india' and not re.search(r'\bindia\b|\bbengaluru\b|\bhyderabad\b|\bpune\b|\bmumbai\b|\bdelhi\b|\bgurugram\b|\blucknow\b|\bchennai\b|\bnoida\b|\bworldwide\b|\banywhere\b|\bglobal\b', job.get('location', ''), re.I):
            continue
        link_key = job['url'].split('?', 1)[0].rstrip('/').lower()
        if link_key in seen: continue
        seen.add(link_key)
        meta = match_job(job, candidate)
        # No unrelated jobs even if they happen to mention Python in the description.
        if not meta['role_match'] and len(meta['matched_skills']) < 2:
            continue
        public = {k:v for k,v in job.items() if not k.startswith('_')}
        public.update(meta)
        public['age_days'] = max(0, (now - date).total_seconds() / 86400)
        output.append(public)
    output.sort(key=lambda j: (-j['match_score'], -published_datetime(j['posted_at']).timestamp()))
    return output[:150]
