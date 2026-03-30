# Data Issues Log

Running log of anomalies, discrepancies, and data quality issues observed during the annual faculty publication data collection. Update this file whenever a new issue is identified or an existing one is resolved.

---

## 2024

**Issue 001 — WoS Auto-Assigned IDs Are Unreliable (Systemic)**

| Field | Detail |
|-------|--------|
| **Date noted** | ~2024 (discovered early in project) |
| **Source** | Web of Science |
| **Faculty affected** | All (systematic) |
| **Issue** | Faculty who have not registered a verified WoS profile still appear in WoS records, but their publications are assigned an auto-generated ID based on name matching. This is unreliable in two directions: (1) faculty with common names may have publications from multiple authors merged under one ID (overcounting); (2) the same faculty member's publications may be split across multiple IDs (undercounting). |
| **Cause** | WoS auto-assigns ResearchIDs algorithmically when a faculty member has not manually claimed and verified their profile. Name disambiguation by algorithm is estimated at ~60% accuracy. |
| **Status** | Resolved — addressed in pipeline design |

**Background:** Several approaches were tried early in the project — fuzzy name matching, second-pass name filtering, name + university filters, and re-searching using auto-generated IDs — but all produced unreliable results (~60% accuracy) and required extensive manual verification. The only reliable solution is a verified WoS profile registered and claimed by the faculty member themselves.

**Resolution:** The current pipeline runs Google Scholar first to generate the Top-N faculty list, then collects verified WoS ResearchIDs directly from those faculty before running WoS extraction. Do not look up faculty by name and use the auto-assigned ID. If a faculty member is missing a verified WoS ResearchID, contact your supervisor to ask them to register and verify their profile at https://www.webofscience.com.

---

## 2026

**Issue 002 — WoS API vs. Website Citation Count Discrepancy**

| Field | Detail |
|-------|--------|
| **Date noted** | 2026-03-23 |
| **Source** | Web of Science |
| **Faculty affected** | All (systematic) |
| **Issue** | Citation counts returned by the WoS Starter API are consistently slightly lower than the counts shown on the WoS website. |
| **Cause** | The WoS Starter API was designed as a metadata-linking tool, not a citation analytics platform. The website aggregates citations across all subscribed databases (Core Collection, BIOSIS, MEDLINE, PQDT, etc.), while the Starter API may not include all non-Core-Collection sub-databases. Clarivate's documentation notes that full citation totals require the WoS Expanded API. |
| **Status** | Monitoring — expected behaviour, not a bug |
| **Resolution** | No code change required. API counts are treated as a consistent lower bound suitable for ranking faculty relative to one another. For definitive absolute counts, the WoS website (logged in via institutional subscription) is more authoritative. Documented in `docs/outlier_report_documentation_2026.md`. |



**Issue 003 — Zero WoS Citations: Newly Created ResearchID Accounts**

| Field | Detail |
|-------|--------|
| **Date noted** | 2026-03-23 |
| **Source** | Web of Science |
| **Faculty affected** | Arthur Korteweg, Stephanie Tully, Luca Cascio Rizzo |
| **Issue** | All three faculty showed zero WoS citations in the initial data pull despite having citations visible on the WoS website. |
| **Cause** | All three registered new WoS ResearchID accounts in 2026. At the time of the initial pull, their accounts existed but citations had not yet propagated into the API database. There is typically a 1–2 month indexing lag for newly created accounts. |
| **Status** | Resolved |
| **Resolution** | Re-fetched WoS data after a few weeks. Citation counts are now correctly reflected in the results. No code change required — this is a data-currency issue. Future note: if a faculty member shows zero WoS citations but has a recently created account, wait 4–6 weeks and re-fetch before concluding there is a problem. |



**Issue 004 — ScholarGPS Profile Verification Needed**

| Field | Detail |
|-------|--------|
| **Date noted** | 2026-03-23 |
| **Source** | ScholarGPS |
| **Faculty affected** | Christian Busch, Erica Jian, Mladen Kolar (and any others flagged by `Outlier_Report.xlsx`) |
| **Issue** | ScholarGPS citation counts for these faculty are significantly off compared to Google Scholar and WoS, suggesting the profile URLs in the faculty list may point to wrong or mismatched profiles. |
| **Cause** | ScholarGPS profiles are matched manually; a URL may link to a different person with a similar name, or the profile may be incomplete. |
| **Status** | Pending — manual verification required |
| **Resolution** | Open each faculty member's `scholargps` URL from `data/Top_50_Faculty_2026.xlsx` in a browser and confirm the profile belongs to the correct person (check name, institution, and publication list). If incorrect, find the right profile URL and update it in `2026_Spring_Faculty_List.xlsx`, then re-run ScholarGPS for the affected faculty. Update this entry once verified. |



**Issue 005 — WoS ResearchID Changed: Patricia Dechow**

| Field | Detail |
|-------|--------|
| **Date noted** | 2026-03-23 |
| **Source** | Web of Science |
| **Faculty affected** | Patricia Dechow |
| **Issue** | WoS data was not fetched for Patricia Dechow — the API returned no results. |
| **Cause** | Her WoS ResearchID changed from `ACM-1387-2022` to `OHU-3285-2025`. The old ID in the faculty list was stale and no longer matched any records in the API. |
| **Status** | Resolved |
| **Resolution** | Updated her ResearchID in `data/Top_50_Faculty_2026.xlsx` (and `2026_Spring_Faculty_List.xlsx`) from `ACM-1387-2022` to `OHU-3285-2025`. Re-ran WoS extraction and aggregation; data now fetches correctly. Future note: if a faculty member shows zero WoS results, check whether their ResearchID has changed on the WoS website before assuming a data-currency issue. |

---



## Template for New Issues

Copy and paste the block below when logging a new issue:

```markdown
### Issue NNN — [Short description]

| Field | Detail |
|-------|--------|
| **Date noted** | YYYY-MM-DD |
| **Source** | WoS / Google Scholar / ScholarGPS / Pipeline |
| **Faculty affected** | Name(s) or "All (systematic)" |
| **Issue** | What was observed |
| **Cause** | Root cause, if known |
| **Status** | Pending / Monitoring / Resolved |
| **Resolution** | What was done, or what action is needed |
```
