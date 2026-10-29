# Module Deep-Dive: Central Configuration (`src/config.py`)

## 1. Technical Concepts & Design Patterns

The `config.py` module establishes the operational baseline for the entire CareerPilot AI system. It implements the **12-Factor Application Configuration Pattern** and uses **Pydantic Settings** for declarative, strictly typed environment management.

### Key Architectural Concepts
1. **Hierarchical Configuration Cascading:** Configuration values are resolved in a strict precedence cascade:
   $$\text{Runtime Parameter Injection} \succ \text{OS Environment Variables} \succ \text{.env File} \succ \text{Hardcoded Class Defaults}$$
2. **Fail-Fast Type Coercion:** Numeric thresholds (such as `minimum_match_threshold: float = 70.0`) are parsed and validated at process initialization. If an invalid type is supplied in the environment (e.g. `MINIMUM_MATCH_THRESHOLD=abc`), the service halts immediately during startup rather than failing silently at runtime.
3. **Graceful Provider Fallback:** Differentiates between primary free providers (Groq LPU, Hugging Face Hub) and optional enterprise fallback providers (OpenAI, Cartesia), enabling full system execution even in zero-cost, purely open-source environments.

---

## 2. Core Classes & Attributes

### `Settings(BaseSettings)`
* **Location:** `src/config.py`
* **Purpose:** Encapsulates all global environment variables, model choices, threshold cutoffs, and external endpoint URLs.

| Attribute Name | Type | Default Value | Environment Key | Description & Architectural Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `app_name` | `str` | `"CareerPilot AI"` | N/A | Human-readable service identifier used in API headers and logs. |
| `log_level` | `str` | `"INFO"` | `LOG_LEVEL` | Logging granularity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `minimum_match_threshold` | `float` | `70.0` | `MINIMUM_MATCH_THRESHOLD` | Percentage cutoff required to pass the XGBoost gate before tailoring resumes. |
| `groq_api_key` | `str` | `""` | `GROQ_API_KEY` | Authentication token for high-throughput Llama-3.3-70B inference via Groq LPU. |
| `groq_model_name` | `str` | `"llama-3.3-70b-versatile"` | N/A | Specific LLM checkpoint used for STAR resume rephrasing. |
| `huggingface_api_key` | `str` | `""` | `HUGGINGFACE_API_KEY` | Optional token for fetching gated embedding models from Hugging Face Hub. |
| `openai_api_key` | `Optional[str]` | `None` | `OPENAI_API_KEY` | Fallback proprietary API key for GPT-4o. |
| `openai_model_name` | `str` | `"gpt-4o"` | N/A | Target OpenAI model checkpoint for fallback operations. |
| `cartesia_api_key` | `Optional[str]` | `None` | `CARTESIA_API_KEY` | API key for Cartesia Sonic ultra-low latency text-to-speech. |
| `residential_proxy_url` | `str` | `""` | `RESIDENTIAL_PROXY_URL` | Optional proxy URL for evading rate limits during ATS board scraping. |
| `hitl_webhook_url` | `str` | `""` | `HITL_WEBHOOK_URL` | Webhook URL (Slack/Discord) for routing pre-submission approval cards. |

* **Side Effects:** Inspects the current working directory for a `.env` file upon import and populates the global singleton instance `settings`.

---

## 3. Concrete Example & Usage

```python
import os
from src.config import Settings, settings

# 1. Access the global singleton configuration
print(f"Active Application: {settings.app_name}")
print(f"Minimum Match Threshold: {settings.minimum_match_threshold}%")
print(f"Primary Groq Model: {settings.groq_model_name}")

# 2. Verify provider availability programmatically
is_groq_enabled = bool(settings.groq_api_key and settings.groq_api_key.startswith("gsk_"))
print(f"Is Groq LPU Configured: {is_groq_enabled}")

# 3. Instantiate an isolated Settings instance for isolated testing
os.environ["MINIMUM_MATCH_THRESHOLD"] = "85.0"
custom_test_settings = Settings()
print(f"Overridden Threshold for Tests: {custom_test_settings.minimum_match_threshold}%")
# Output: 85.0
```
