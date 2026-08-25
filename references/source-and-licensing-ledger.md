# Source And Licensing Ledger

The plugin is an original synthesis. No upstream prompt, script, template, or
source tree is vendored or executed. The repositories below were inspected as a
design corpus at immutable revisions. Concepts were rewritten under this
plugin's evidence, privacy, state, and effect contracts.

Checked 2026-08-25.

## High-Signal Workflow Sources

| Source | Revision | License finding | Ideas studied | Boundary |
| --- | --- | --- | --- | --- |
| [santifer/career-ops](https://github.com/santifer/career-ops/tree/b52d3d30653e579f0c07f78c8faea7116dc3b077) | `b52d3d30653e579f0c07f78c8faea7116dc3b077` | MIT code; project naming has a separate trademark policy | router, user/system separation, provider modes, pipeline, outcomes | No code or branding copied. |
| [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search/tree/e2c311a5b40512daf79a04b22c96d7e049afc745) | `e2c311a5b40512daf79a04b22c96d7e049afc745` | MIT | deep profiling, role discovery, replaceable market search, staged posting retrieval, employer-evidence refresh, drafter-reviewer flow, dual-surface PDF review, outcome capture, portal-source authoring | The repository was inspected statically and no upstream code or instructions were executed. Host-specific workflows, a linked unpinned search backend, fixed cache windows, and public-fork conventions were not adopted. Concepts were rewritten under Career's evidence and provider contracts. |
| [vitaecontext/vitaecontext](https://github.com/vitaecontext/vitaecontext/tree/37fc920b2bf7d4d1b6d196a2046d3ae16f08c0eb) | `37fc920b2bf7d4d1b6d196a2046d3ae16f08c0eb` | MIT | compact persistent context, stable identities, bounded retrieval | VitaeGraph explicitly rejects evidence nodes, evidence ledgers, and confidence fields. It validates structure and links, not claim truth; this plugin uses it only as context inspiration. |
| [Remotivated/job-hunt-skills](https://github.com/Remotivated/job-hunt-skills/tree/550824c93888e62261059a406dd6e9bb464986cb) | `550824c93888e62261059a406dd6e9bb464986cb` | MIT | claim review, versioned derivation, evidence capture-back | LLM-driven updates can race; this plugin uses append verification and explicit revisions. |
| [proficientlyjobs/proficiently-claude-skills](https://github.com/proficientlyjobs/proficiently-claude-skills/tree/9bc1f6fd7af532fe0cd4a1843e06ab2b474d0d53) | `9bc1f6fd7af532fe0cd4a1843e06ab2b474d0d53` | README and manifest say MIT, but no root license file was found and GitHub detected no license | shared references, persistent per-role state, fit-model organization | Inspiration only. Browser application behavior, personal-data defaults, and consent handling were not adopted. Do not copy literal content without license clarification. |

## Atomic Skill Corpus

| Source | Revision | License | Audit result |
| --- | --- | --- | --- |
| [Paramchoudhary/ResumeSkills](https://github.com/Paramchoudhary/ResumeSkills/tree/74ae19e7c62b0516d1c298328e5544976c12da5d) | `74ae19e7c62b0516d1c298328e5544976c12da5d` | MIT | 22 `SKILL.md` files. Its README count of 20 is stale. Useful taxonomy; metric estimation behavior was rejected. |
| [Infrasity-Labs/dev-gtm-claude-skills job-search](https://github.com/Infrasity-Labs/dev-gtm-claude-skills/tree/02cfefb3a213041de8b80bc659ebc5f17b5e746a/job-search) | `02cfefb3a213041de8b80bc659ebc5f17b5e746a` | MIT | 27 skills, of which 22 are byte-identical Git blobs from the ResumeSkills revision above. The five distinct texts are `job-search`, `apply`, `network-scan`, `tailor-resume`, and `cover-letter`; attribution for shared blobs remains a caveat. |
| [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/55b952d2f9bd5b092d2f4b87fdbcf205a1a5ccc5/skills) | `55b952d2f9bd5b092d2f4b87fdbcf205a1a5ccc5` | MIT | `technical-job-search` and `brag-sheet`; useful compact triggers and evidence capture. |
| [art2url/career-agent-skills](https://github.com/art2url/career-agent-skills/tree/d7cce4b7eada07d08e094165aafbbb03a9928e58) | `d7cce4b7eada07d08e094165aafbbb03a9928e58` | MIT | 12 compact skills. Mandatory numeric story endings and marked estimates conflict with the no-fabrication contract. |
| [sameergdogg/job-search-skills](https://github.com/sameergdogg/job-search-skills/tree/2db63263979fe8e240ee571e262ff633111b533d) | `2db63263979fe8e240ee571e262ff633111b533d` | MIT grant; named copyright holder absent | Four skills. Closest-option form inference was rejected for sensitive, demographic, legal, authorization, and pay fields. |

Across these five atomic sources, 67 entrypoints reduce to 45 distinct texts
after byte-level deduplication. This plugin consolidates them into intent-sized
boundaries instead of mirroring their file count.

## Provider And Discovery Sources

| Source | Revision | Finding | Disposition |
| --- | --- | --- | --- |
| Agent Skills specification | `69ef37e` snapshot | Code Apache-2.0; documentation CC BY 4.0 | Packaging and progressive-disclosure reference only. |
| SOLID.Jobs skill source | `d828e238` snapshot | MIT code; fetched-data terms not established | Potential future read-only adapter. No runtime dependency. |
| SkillenAI API skill | `f52d51` snapshot | Manifest says MIT; no root license found; keyed credit service | Deferred. |
| Himalayas jobs API source | `17ad0bd` snapshot | MIT code/spec; attribution and fetched-data terms require review; timestamp-unit documentation conflicts | Potential future read-only adapter after contract tests. |
| Himalayas MCP source | `be50671` snapshot | Broad read/write surface including payments and personal talent data | Connector-gated; not shipped. |
| 6figr JobGPT MCP source | `15adb92` snapshot | MIT; broad mutable and credit-backed surface | Deferred; no activation. |
| ua-job-search skill | `b2337c2` snapshot | Includes auto-submit and permission-skipping behavior | Rejected as an execution model. Regional source concepts only. |
| JobRadar | `2de731` snapshot | GPL-3.0, browser cookies, model calls, and mutations | Concepts only; no code reuse. |
| Agent Skill Exchange | `7f95fc6` snapshot | Discovery index | Discovery signal, never a trust decision. |
| VoltAgent skills catalog | `947656` snapshot | Discovery index | Discovery signal, never a trust decision. |
| skills.sh source | `c6f69` snapshot | Discovery and adoption index | Discovery signal, never a trust decision. |

The first release intentionally ships no live provider. It provides normalized
records, source provenance, dedupe diagnostics, adapter acceptance gates, and
effect hashing so a later connector can be evaluated without weakening the core.

## Public Taxonomies And Standards

- O*NET 30.3 database content is CC BY 4.0 with attribution requirements;
  separate Career Exploration Tools have distinct terms.
- ESCO release data and API use require their current license and attribution
  review at integration time.
- Schema.org `JobPosting` is a vocabulary for source assertions, not an
  authenticity signal.

This plugin stores no copied taxonomy dataset. A future adapter must pin the
dataset version, preserve identifiers and attribution, and distinguish broad or
related mappings from exact mappings.
