"""Tests for resume-driven interview across PDF, DOCX, TXT and answer feedback."""
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from src.voice_agent import app
from src.interview_service import build_interview_plan, parse_resume

CLIENT = TestClient(app)
SAMPLE = """Aarav Mehta
EDUCATION
B.Tech Computer Science at Example University
TECHNICAL SKILLS
Python, FastAPI, Docker, SQL
PROJECTS
Smart Expense Tracker
Developed FastAPI endpoints, SQL queries, and database tables for tracking expenses.
Recipe Recommendation Engine
Built a Python recipe recommender using user preferences and Pandas data cleaning.
EXPERIENCE
Software Intern at Example Company
Created API endpoints and wrote tests.
"""


def make_docx():
    doc = Document()
    for line in SAMPLE.splitlines():
        doc.add_paragraph(line)
    data = BytesIO()
    doc.save(data)
    return data.getvalue()


def make_pdf():
    data = BytesIO()
    c = canvas.Canvas(data)
    y = 790
    for line in SAMPLE.splitlines():
        c.drawString(40, y, line)
        y -= 17
    c.save()
    return data.getvalue()


def test_resume_text_parsing():
    candidate = parse_resume(SAMPLE)
    assert candidate['name'] == 'Aarav Mehta'
    assert 'FastAPI' in candidate['skills']
    assert len(candidate['bullets']) == 2
    assert 'Smart Expense Tracker' in candidate['bullets'][0]
    assert 'Recipe Recommendation Engine' in candidate['bullets'][1]


def test_upload_pdf_docx_txt_and_interview_plan():
    for filename, raw in (('cv.txt', SAMPLE.encode()),('cv.docx',make_docx()), ('cv.pdf', make_pdf())):
        response = CLIENT.post('/api/resume/upload', files={'file':(filename, raw)})
        assert response.status_code == 200, (filename,response.text)
        candidate = response.json()['candidate']
        assert candidate['name'] == 'Aarav Mehta', filename
        assert any('Smart Expense Tracker' in project for project in candidate['bullets']), filename
        plan = CLIENT.post('/api/interview/plan',json={'candidate':candidate})
        assert plan.status_code == 200
        questions = plan.json()['questions']
        assert 24 <= len(questions) <= 28
        assert 'introduce yourself' in questions[0]['question'].lower()
        assert any('Smart Expense Tracker' in q['question'] for q in questions)
        assert any('Recipe Recommendation Engine' in q['question'] for q in questions)
        assert any('FastAPI' in q['question'] for q in questions)
        stages = [int(q['stage'].split()[1]) for q in questions]
        assert stages == sorted(stages)
        assert questions[-1]['category'] == 'Closing'


def test_contextual_feedback_without_api_key(monkeypatch):
    from src.config import settings
    monkeypatch.setattr(settings,'groq_api_key','')
    candidate = parse_resume(SAMPLE)
    question = build_interview_plan(candidate)['questions'][2]
    response = CLIENT.post('/api/interview/feedback',json={
        'candidate':candidate, 'question':question,
        'answer':'I built an expense tracker with FastAPI and SQL. It supports saving transactions.'
    })
    assert response.status_code == 200
    data = response.json()
    assert data['follow_up']
    assert data['assessment_mode'] == 'practice_heuristic'
    assert 'not a verified' in data['assessment_note']


def test_reject_unsupported_and_empty_pdfs():
    response = CLIENT.post('/api/resume/upload',files={'file':('cv.exe',b'not a resume')})
    assert response.status_code == 400
    # A valid but empty PDF should fail rather than hallucinate projects.
    pdf = BytesIO()
    c=canvas.Canvas(pdf)
    c.showPage()
    c.save()
    response = CLIENT.post('/api/resume/upload',files={'file':('empty.pdf',pdf.getvalue())})
    assert response.status_code == 422


def test_many_projects_still_covered():
    candidate = {'name':'Sample', 'role':'Engineer', 'degree':'B.Tech', 'skills':['Python'],
                 'bullets':[f'Project {i}: Built a useful prototype' for i in range(8)]}
    plan = build_interview_plan(candidate)
    for i in range(8):
        assert any(f'Project {i}' in q['category'] for q in plan['questions'])
