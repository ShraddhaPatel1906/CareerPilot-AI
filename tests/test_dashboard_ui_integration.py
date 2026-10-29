"""Dashboard integration regression checks; no internet or browser installation needed."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / 'frontend' / 'index.html').read_text(encoding='utf-8')


def test_ats_uses_live_job_results_not_sample_companies():
    assert 'Recent Jobs Matching Your Resume' in HTML
    assert 'liveJobs.map(liveJobAsTarget)' in HTML
    assert 'function syncComparisonJobs()' in HTML
    assert 'Select a recent job to compare.' in HTML
    assert 'const job = targetJobs[currentJobIndex]' in HTML
    assert 'id="scoring-days"' in HTML
    assert 'zepto_ai_ml' not in HTML
    assert 'swiggy_ds' not in HTML


def test_tailoring_and_ats_share_selected_target():
    assert 'function selectMatchedJob(index)' in HTML
    assert 'tailorJobIndex = index;' in HTML
    assert 'id="tailored-resume-preview"' in HTML
    assert 'id="tailored-resume-full-text"' in HTML
    assert 'function copyVerifiedBullet(index)' in HTML
    assert 'if (job?.isLive && job.url)' in HTML


def test_no_misleading_claims_in_dashboard():
    assert 'not an employer ATS result' in HTML
    assert 'No invented metrics or skills' in HTML
    assert 'not a live listing' in HTML
    assert 'ATS Match Boost: +30%' not in HTML
    assert 'Cutoff Gate: 70.0%' not in HTML
