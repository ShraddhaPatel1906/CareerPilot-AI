"""No external network: fixture-based real feed parsing, date verification, API and safety tests."""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from src.live_jobs import (
    parse_remotive, parse_arbeitnow, parse_jobicy, parse_lever, parse_greenhouse,
    query_jobs, employer_apply_email, safe_url, published_datetime
)
from src.voice_agent import app

CLIENT = TestClient(app)
NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(days=1)).isoformat()
OLD = (NOW - timedelta(days=8)).isoformat()
CANDIDATE = {'role':'Data Scientist / AI Engineer', 'skills':['Python', 'FastAPI', 'SQL', 'Machine Learning']}


def test_remotive_extracts_real_url_and_published_date():
    parsed = parse_remotive({'jobs':[
        {'id':101,'title':'Junior Data Scientist','company_name':'Example Co',
         'candidate_required_location':'Worldwide', 'url':'https://remotive.com/remote-jobs/example',
         'publication_date':RECENT,'description':'<p>Apply with Python, SQL. Send your resume to careers@example.com</p>'},
        {'id':102,'title':'Machine Learning Intern','company_name':'Old Corp',
         'candidate_required_location':'India','url':'https://remotive.com/old',
         'publication_date':OLD,'description':'Python'}]})
    assert len(parsed)==2
    assert parsed[0]['email_to_apply']=='careers@example.com'
    matches=query_jobs(parsed,CANDIDATE,days=3,now=NOW)
    assert len(matches)==1
    assert matches[0]['title']=='Junior Data Scientist'
    assert matches[0]['match_score'] > 0
    assert matches[0]['url'].startswith('https://')
    assert matches[0]['source']=='Remotive'
    assert '_full_description' not in matches[0]


def test_other_live_providers_only_use_publish_date():
    a = parse_arbeitnow({'data':[{'slug':'abc','title':'Data Analyst','company_name':'Example Inc',
        'location':'India','remote':False,'url':'https://www.arbeitnow.com/jobs/abc',
        'created_at':int((NOW-timedelta(hours=3)).timestamp()),'description':'Python SQL'}]})
    assert len(a)==1
    assert a[0]['location']=='India'
    lever=parse_lever([{'id':'xyz','text':'AI Engineer','hostedUrl':'https://jobs.lever.co/example/xyz',
         'createdAt':int((NOW-timedelta(hours=1)).timestamp()*1000),
         'categories':{'location':'Remote'},'descriptionPlain':'FastAPI Python'}],'example')
    assert len(lever)==1
    assert lever[0]['posted_at']
    assert parse_greenhouse({'jobs':[{'id':'xyz','title':'Data Engineer',
        'updated_at':RECENT,'absolute_url':'https://boards.greenhouse.io/example/jobs/123',
        'location':{'name':'Mumbai'},'content':'SQL'}]}, 'example') == []


def test_untrusted_urls_and_email_not_misrepresented():
    assert safe_url('javascript:alert(1)') is None
    assert safe_url('http://employer.com/apply') is None
    assert safe_url('https://site.com/path')
    assert employer_apply_email('Support: support@example.com') is None
    assert employer_apply_email('Please email your resume to hiring@example.com')=='hiring@example.com'
    assert published_datetime('not a date') is None


def test_job_endpoint_uses_real_feeds_no_fixtures(monkeypatch):
    from src import voice_agent
    fake_jobs = parse_remotive({'jobs':[{'id':8,'title':'AI Engineer Intern','company_name':'Real Example',
        'candidate_required_location':'India','url':'https://remotive.com/real',
        'publication_date':datetime.now(timezone.utc).isoformat(),
        'description':'Must know Python, Machine Learning and FastAPI'}]})
    async def mock_feed():
        return fake_jobs, ['remotive'], []
    monkeypatch.setattr(voice_agent,'load_public_jobs',mock_feed)
    r=CLIENT.post('/api/jobs/recent',json={'candidate':CANDIDATE,'days':3,'location':'india'})
    assert r.status_code==200,r.text
    assert len(r.json()['jobs'])==1
    assert r.json()['jobs'][0]['url']=='https://remotive.com/real'
    assert r.json()['sources_ok']==['remotive']
    assert CLIENT.post('/api/jobs/recent',json={'candidate':CANDIDATE,'days':99}).status_code == 422


def test_failed_feeds_do_not_fall_back_to_fake_jobs(monkeypatch):
    from src import voice_agent
    async def fail():return [],[],['remotive: ConnectError']
    monkeypatch.setattr(voice_agent,'load_public_jobs',fail)
    r=CLIENT.post('/api/jobs/recent',json={'candidate':CANDIDATE})
    assert r.status_code==503
    assert 'No demo jobs' in r.json()['detail']


def test_resume_upload_extracts_contact_email():
    resume='''Sana Kapoor\nsana.kapoor@example.com\nEDUCATION\nM.Sc. Computer Science\nSKILLS\nPython, SQL, Machine Learning\nPROJECTS\nAI Interview App\nBuilt FastAPI application and deployed a service.'''
    r=CLIENT.post('/api/resume/upload',files={'file':('cv.txt',resume.encode())})
    assert r.status_code==200
    assert r.json()['candidate']['email']=='sana.kapoor@example.com'


def test_jobicy_public_feed_parsing():
    jobs=parse_jobicy({'jobs':[{'id':10,'jobTitle':'Python Data Engineer','companyName':'Example Remote',
       'jobGeo':'Remote','url':'https://jobicy.com/jobs/example', 'pubDate':RECENT,
       'jobDescription':'Must know Python and SQL'}]})
    assert len(jobs)==1
    assert jobs[0]['source']=='Jobicy'
    assert query_jobs(jobs,CANDIDATE,days=3,now=NOW)


def test_job_description_handles_encoded_html_headings_and_bullets():
    from src.live_jobs import to_text, normalize_job
    raw = '&lt;h3&gt;&lt;strong&gt;Who/What is Artefact?&lt;/strong&gt;&lt;/h3&gt; &lt;p&gt;Artefact is a data and AI consulting firm.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;'
    result = to_text(raw)
    assert 'Who/What is Artefact?' in result
    assert 'Artefact is a data and AI consulting firm.' in result
    assert '• Python' in result and '• SQL' in result
    assert '<h3>' not in result and '&lt;' not in result
    job = normalize_job(source='Remotive', external_id='a', title='Data Scientist', company='Artefact', location='India', url='https://example.com/apply', posted=RECENT, description=raw)
    assert job is not None and '<h3>' not in job['description']


def test_double_encoded_html_and_script_are_not_displayed():
    from src.live_jobs import to_text
    raw = '&amp;lt;h3&amp;gt;Requirements&amp;lt;/h3&amp;gt;&amp;lt;p&amp;gt;Python and SQL&amp;lt;/p&amp;gt;'
    assert to_text(raw) == 'Requirements\nPython and SQL'
    assert 'alert' not in to_text('<p>ML Engineer</p><script>alert(123)</script><style>body{display:none}</style>')
    assert '<script' not in to_text('<p>ML Engineer</p><script>alert(123)</script>')
