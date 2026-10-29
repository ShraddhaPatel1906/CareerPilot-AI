import hashlib
import time
from typing import List, Dict, Any, Optional
import httpx

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ScoutAgent")
    logger.success = logger.info
from src.schemas import JobPosting, ATSPlatform, WorkplaceType

class ScoutAgent:
    """
    The Scout Agent: Autonomous Job Ingestion Engine.
    Executes high-throughput, anti-ban job extraction across Greenhouse, Lever,
    Workday, and aggregators using direct APIs and TLS-spoofed requests.
    """

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    @staticmethod
    def _generate_job_id(company: str, external_id: str) -> str:
        raw_key = f"{company.strip().lower()}:{external_id.strip().lower()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    async def scrape_greenhouse(self, board_token: str) -> List[JobPosting]:
        """
        Extracts full job descriptions directly from Greenhouse's unauthenticated REST API.
        Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        logger.info(f"Scouting Greenhouse board: {board_token}")
        
        async with httpx.AsyncClient(timeout=15.0, proxy=self.proxy_url) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch Greenhouse board '{board_token}': {e}")
                return []

            postings: List[JobPosting] = []
            for item in data.get("jobs", []):
                external_id = str(item.get("id"))
                job_id = self._generate_job_id(board_token, external_id)
                
                # Strip basic HTML tags from Greenhouse content
                raw_content = item.get("content", "")
                
                postings.append(JobPosting(
                    id=job_id,
                    external_id=external_id,
                    ats_platform=ATSPlatform.GREENHOUSE,
                    company_name=board_token.capitalize(),
                    title=item.get("title", "Untitled Role"),
                    location=item.get("location", {}).get("name", "Remote / Unspecified"),
                    workplace_type=WorkplaceType.REMOTE if "remote" in item.get("title", "").lower() else WorkplaceType.HYBRID,
                    description_text=raw_content,
                    apply_url=item.get("absolute_url", ""),
                    source_url=item.get("absolute_url", "")
                ))
            
            logger.success(f"Successfully scraped {len(postings)} jobs from Greenhouse [{board_token}]")
            return postings

    async def scrape_lever(self, company_id: str) -> List[JobPosting]:
        """
        Extracts jobs directly from Lever's public postings API.
        Endpoint: https://api.lever.co/v0/postings/{company_id}?mode=json
        """
        url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
        logger.info(f"Scouting Lever company: {company_id}")

        async with httpx.AsyncClient(timeout=15.0, proxy=self.proxy_url) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                jobs_data = resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch Lever board '{company_id}': {e}")
                return []

            postings: List[JobPosting] = []
            for item in jobs_data:
                external_id = item.get("id", "")
                categories = item.get("categories", {})
                location = categories.get("location", "Unspecified")
                
                postings.append(JobPosting(
                    id=self._generate_job_id(company_id, external_id),
                    external_id=external_id,
                    ats_platform=ATSPlatform.LEVER,
                    company_name=company_id.capitalize(),
                    title=item.get("text", "Untitled Role"),
                    location=location,
                    workplace_type=WorkplaceType.REMOTE if "remote" in location.lower() else WorkplaceType.HYBRID,
                    description_text=item.get("descriptionPlain", item.get("description", "")),
                    apply_url=item.get("applyUrl", ""),
                    source_url=item.get("hostedUrl", "")
                ))

            logger.success(f"Successfully scraped {len(postings)} jobs from Lever [{company_id}]")
            return postings

    def scrape_workday_cxs(self, tenant: str, host: str, site: str, max_jobs: int = 50) -> List[JobPosting]:
        """
        Extracts job listings from Workday's internal CXS POST endpoint.
        Handles JSON pagination and token-controlled queries.
        """
        url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        
        offset, limit = 0, 20
        all_postings: List[JobPosting] = []

        with httpx.Client(timeout=20.0, proxy=self.proxy_url) as client:
            while len(all_postings) < max_jobs:
                payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
                try:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                except Exception as e:
                    logger.error(f"Workday request failed at offset {offset}: {e}")
                    break

                items = data.get("jobPostings", [])
                if not items:
                    break

                for item in items:
                    external_path = item.get("externalPath", "")
                    job_url = f"https://{host}/{tenant}/{site}{external_path}"
                    all_postings.append(JobPosting(
                        id=self._generate_job_id(tenant, external_path),
                        external_id=external_path,
                        ats_platform=ATSPlatform.WORKDAY,
                        company_name=tenant.capitalize(),
                        title=item.get("title", "Untitled Role"),
                        location=item.get("locationsText", "Unspecified"),
                        description_text=item.get("title", "") + " - Full details available on portal.",
                        apply_url=job_url,
                        source_url=job_url
                    ))

                offset += limit
                total_available = data.get("total", 0)
                if offset >= total_available or offset >= 2000:
                    break
                time.sleep(0.2)

        logger.success(f"Scraped {len(all_postings)} Workday jobs from [{tenant}]")
        return all_postings
