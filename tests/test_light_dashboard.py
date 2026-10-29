"""Frontend redesign regression checks; no external services required."""
from pathlib import Path
from bs4 import BeautifulSoup

HTML = (Path(__file__).resolve().parents[1] / 'frontend' / 'index.html').read_text(encoding='utf-8')
DOC = BeautifulSoup(HTML, 'html.parser')


def test_clean_light_theme_and_short_navigation():
    assert 'class="light"' in HTML
    assert '--cp-page: #f8fafc' in HTML
    labels = ['ATS Match', 'Resume Tailor', 'Mock Interview', 'Live Jobs']
    nav = DOC.find('nav',attrs={'aria-label':'Main navigation'})
    assert nav is not None
    for label in labels:
        assert label in nav.get_text(' ',strip=True)
    assert 'Engine Active' not in nav.get_text(' ',strip=True)
    assert 'Predictive ATS Optimization, Resume Tailoring & In-Depth' not in nav.get_text(' ',strip=True)


def test_existing_bindings_and_handlers_preserved():
    ids = ['file-upload-input','tab-btn-scoring','tab-btn-tailoring','tab-btn-voice',
           'tab-btn-applicator','live-days','live-location','stat-total-jobs',
           'stat-applied-count','stat-ready-count','hub-resume-name',
           'company-cards-container','recent-match-jobs','job-dropdown',
           'tailor-job-select','tailored-bullets-container','tailored-resume-preview',
           'voice-question-text','voice-answer-textarea','score-display']
    for key in ids:
        assert len(DOC.find_all(id=key)) == 1, key
    for fn in ['switchTab','renderCandidateUI','fetchLiveJobBoards','renderApplicatorHub',
               'renderJobUI','selectMatchedJob','renderTailoringUI',
               'loadInterviewQuestionsFromBackend','draftApplicationEmail']:
        assert f'function {fn}(' in HTML or f'async function {fn}(' in HTML,fn


def test_reduced_visual_clutter_and_safety_text_retained():
    assert 'Live Job Opportunities' in HTML
    assert 'Recent openings matched to your resume.' in HTML
    assert 'How does STAR work?' in HTML
    assert 'Job sources & application information' in HTML
    assert 'not an employer ATS result' in HTML
    assert 'No invented metrics or skills' in HTML
    assert 'not a live listing' in HTML
    assert 'no application is sent automatically' in HTML
