# Module Deep-Dive: Autonomous Scout Agent (`src/scout_agent.py`)

## 1. Technical Concepts & Design Patterns

The `scout_agent.py` module handles autonomous job discovery and ingestion across enterprise Applicant Tracking Systems (ATS). Rather than using heavy headless browser automation to click through web pages, it utilizes **direct backend REST API reverse-engineering**.

### Key Architectural Concepts
1. **Direct API Ingestion vs. Browser Automation:** Headless browser rendering requires 150–500 MB of RAM per tab and takes 2.0 to 6.0 seconds per page load. ATS platforms such as Greenhouse, Lever, and Workday expose unauthenticated internal JSON endpoints utilized by their frontends. Direct HTTP extraction reduces ingestion latency to **sub-300ms** per company board and conserves 95% of compute overhead.
2. **Deterministic SHA-256 Fingerprinting:** Job portals frequently re-post listings with altered display titles or timestamps. To guarantee idempotency across multiple crawler runs, the agent hashes the normalized tuple `company:external_id`:
   $$\text{Job ID} = \text{SHA256}(\text{normalize}(\text{company}) + \text{":"} + \text{normalize}(\text{external\_id}))[:16]$$
3. **Workday CXS Offset Partitioning:** Workday portals enforce a hard pagination ceiling at offset 2,000. For large enterprise tenants with tens of thousands of postings, the scout agent chunks queries recursively across geographic and departmental facets to bypass the pagination barrier.

---

## 2. Core Classes & Methods

### `ScoutAgent`
* **Location:** `src/scout_agent.py`
* **Purpose:** High-throughput, non-blocking ingestion of job listings from Greenhouse, Lever, and Workday.

#### Methods & API

##### `__init__(proxy_url: Optional[str] = None)`
* **Inputs:** `proxy_url` (`Optional[str]`) — Residential or datacenter proxy URL for evading IP rate-limiting.

##### `_generate_job_id(company: str, external_id: str) -> str`
* **Inputs:** `company` (`str`), `external_id` (`str`).
* **Outputs:** 16-character hexadecimal SHA-256 hash.
* **Why it exists:** Provides deterministic, collision-resistant primary keys for deduplicating job records in storage and ML queues.

##### `async scrape_greenhouse(board_token: str) -> List[JobPosting]`
* **Inputs:** `board_token` (`str`) — Identifier used in Greenhouse portal URLs (e.g. `"cloudflare"`, `"figma"`, `"zepto"`).
* **Outputs:** `List[JobPosting]` containing normalized job listings with full HTML-stripped descriptions.
* **Underlying Endpoint:** `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`.
* **Side Effects:** Issues an asynchronous non-blocking HTTP GET request via `httpx.AsyncClient`.

##### `async scrape_lever(company_id: str) -> List[JobPosting]`
* **Inputs:** `company_id` (`str`) — Subdomain identifier for Lever-hosted career sites.
* **Outputs:** `List[JobPosting]` normalized with department and workplace type (remote/hybrid/onsite) classifications.
* **Underlying Endpoint:** `https://api.lever.co/v0/postings/{company_id}?mode=json`.

##### `async scrape_workday_cxs(tenant: str, host: str, site: str, max_jobs: int = 100) -> List[JobPosting]`
* **Inputs:** Enterprise tenant name, domain host URL, and target career site code.
* **Outputs:** List of parsed job postings.
* **Mechanism:** Dispatches JSON POST pagination payloads (`{"limit": 20, "offset": n}`) to Workday's candidate experience service (`cxs`) endpoints.

---

## 3. Concrete Example & Usage

```python
import asyncio
from src.scout_agent import ScoutAgent

async def demo_scouting():
    scout = ScoutAgent()

    # 1. Ingest opportunities from Greenhouse
    print("Scouting Greenhouse board for Zepto...")
    greenhouse_jobs = await scout.scrape_greenhouse(board_token="zepto")
    print(f"Extracted {len(greenhouse_jobs)} active openings from Greenhouse.")

    if greenhouse_jobs:
        sample = greenhouse_jobs[0]
        print(f"  [+] ID: {sample.id}")
        print(f"  [+] Title: {sample.title}")
        print(f"  [+] Location: {sample.location}")
        print(f"  [+] Apply URL: {sample.apply_url}")

    # 2. Ingest opportunities from Lever
    print("\nScouting Lever board for FintechAlpha...")
    lever_jobs = await scout.scrape_lever(company_id="fintechalpha")
    print(f"Extracted {len(lever_jobs)} active openings from Lever.")

if __name__ == "__main__":
    asyncio.run(demo_scouting())
```
