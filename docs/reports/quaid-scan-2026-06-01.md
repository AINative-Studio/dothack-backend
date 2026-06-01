# quaid-scanner Report: /Users/karstenwade/Projects/AINative-Studio/src/dothack-backend

**Score:** 🔴 2.0/10 — CRITICAL risk
**Maturity:** sandbox | **Depth:** standard | **Duration:** 0.1s
**Scanned:** 2026-06-01T21:29:31.289Z

## Pillar Scores

| Pillar | Score | Weight | Findings |
|--------|-------|--------|----------|
| Security | 2.0 | 25% | 0C 5W 1I |
| Governance | 1.5 | 20% | 0C 2W 11I |
| Community | 2.5 | 15% | 0C 2W 9I |
| AI Readiness | 2.5 | 15% | 0C 5W 0I |
| Inclusive Language | 0.0 | 15% | 0C 4W 18I |
| Technical Rigor | 4.5 | 10% | 1C 1W 2I |

## Critical Findings

### test-coverage-1
**Pillar:** Technical Rigor | **Category:** test-coverage

No test files detected in the repository

_(source: local file check)_

**Suggestion:** Add a test suite to improve code reliability and enable coverage tracking

**Reference:** https://chaoss.community/metric-test-coverage/

## Warnings

- **[TIMEOUT-binary-artifacts]** Scanner "binary-artifacts" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-dep-pinning-docker]** Scanner "dep-pinning-docker" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-openssf-local-checks]** Scanner "openssf-local-checks" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-openssf-scorecard]** Scanner "openssf-scorecard" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-token-permissions]** Scanner "token-permissions" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[license-content-validation-1]** No LICENSE file found in repository root *(Add a LICENSE file with a recognized open source license)*
- **[TIMEOUT-license-header-scanner]** Scanner "license-header-scanner" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[psych-safety-1]** No Code of Conduct found *(Add a CODE_OF_CONDUCT.md — see https://www.contributor-covenant.org/)*
- **[support-channels-1]** No SUPPORT.md or .github/SUPPORT.md found *(Add a SUPPORT.md documenting how users can get help)*
- **[agentic-rules-2]** CLAUDE.md lacks recognized structural sections *(Add sections like "Critical Rules", "Project Structure", "Common Tasks" to improve agent guidance.)*
- **[TIMEOUT-ai-repo-detection]** Scanner "ai-repo-detection" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-dataset-provenance]** Scanner "dataset-provenance" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-model-card-detection]** Scanner "model-card-detection" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-model-card-scoring]** Scanner "model-card-scoring" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-diminishing-language-scanner]** Scanner "diminishing-language-scanner" timed out after undefinedms *(Increase scannerTimeout in configuration or check network connectivity)*
- **[TIMEOUT-inclusive-code-scanner]** Scanner "inclusive-code-scanner" failed: Cannot read properties of undefined (reading 'termListUrl') *(Check scanner implementation for errors)*
- **[TIMEOUT-inclusive-doc-scanner]** Scanner "inclusive-doc-scanner" failed: Cannot read properties of undefined (reading 'termListUrl') *(Check scanner implementation for errors)*
- **[TIMEOUT-inclusive-naming-scanner]** Scanner "inclusive-naming-scanner" failed: Cannot read properties of undefined (reading 'termListUrl') *(Check scanner implementation for errors)*
- **[interaction-templates-1]** No issue templates configured *(Add .github/ISSUE_TEMPLATE/ with bug report and feature request templates)*

## Info

- **[branch-protection-1]** GitHub token not provided. Cannot check branch protection settings.
- **[asset-protection-1]** No trademark policy found (optional)
- **[asset-protection-2]** No export control documentation found (optional)
- **[asset-protection-3]** No CLA or DCO requirement detected
- **[asset-protection-4]** Contributor friction level: Low
- **[bus-factor-1]** Bus factor: 1, Elephant factor: 51% (4 contributors, 45 commits in last 12 months)
- **[dep-license-scanning-1]** Python dependencies detected (requirements.txt) — license scanning requires installed packages
- **[governance-classification-1]** No governance model detected — governance files exist but no recognizable model pattern found
- **[governance-detection-1]** No governance documentation found
- **[license-compatibility-1]** Cannot check license compatibility — no LICENSE file found
- **[vendor-neutrality-domain-count]** Found 3 unique email domain(s) across 45 commits
- **[vendor-neutrality-no-succession]** No succession planning documentation found
- **[burnout-detection-1]** Burnout detection requires a GitHub token
- **[contributor-data-2]** Contributor emails span 3 domains
- **[contributor-funnel-1]** Contributor funnel: 0 core, 3 regular, 1 casual (4 total)
- **[funding-1]** No funding infrastructure detected
- **[issue-closure-1]** Issue closure analysis requires a GitHub token
- **[response-classification-1]** Response classification requires a GitHub token
- **[response-time-1]** Response time analysis requires a GitHub token
- **[stale-bot-1]** No stale bot configured
- **[support-channels-2]** README contains a support/help section
- **[AK-GIT-CLONE-README.md:137]** Assumed knowledge: "clone" operation used without explanation
- **[AK-GIT-CLONE-README.md:139]** Assumed knowledge: "clone" operation used without explanation
- **[AK-GIT-FORK-README.md:390]** Assumed knowledge: "fork" operation used without explanation
- **[AK-GIT-BRANCH-README.md:391]** Assumed knowledge: "branch" operation used without explanation
- **[AK-ACRONYM-LICENSE-README.md:5]** Undefined acronym "LICENSE" may confuse newcomers
- **[AK-ACRONYM-PRD-README.md:6]** Undefined acronym "PRD" may confuse newcomers
- **[AK-ACRONYM-LLM-README.md:15]** Undefined acronym "LLM" may confuse newcomers
- **[AK-ACRONYM-RLHF-README.md:15]** Undefined acronym "RLHF" may confuse newcomers
- **[AK-ACRONYM-ARCHITECTURE-README.md:22]** Undefined acronym "ARCHITECTURE" may confuse newcomers
- **[AK-ACRONYM-BAAI-README.md:47]** Undefined acronym "BAAI" may confuse newcomers
- **[AK-ACRONYM-TDD-README.md:74]** Undefined acronym "TDD" may confuse newcomers
- **[AK-ACRONYM-README-README.md:121]** Undefined acronym "README" may confuse newcomers
- **[AK-ACRONYM-POST-README.md:256]** Undefined acronym "POST" may confuse newcomers
- **[AK-ACRONYM-GET-README.md:257]** Undefined acronym "GET" may confuse newcomers
- **[AK-ACRONYM-PATCH-README.md:259]** Undefined acronym "PATCH" may confuse newcomers
- **[AK-ACRONYM-DELETE-README.md:260]** Undefined acronym "DELETE" may confuse newcomers
- **[AK-ACRONYM-MVP-README.md:411]** Undefined acronym "MVP" may confuse newcomers
- **[AK-ACRONYM-CRUD-README.md:415]** Undefined acronym "CRUD" may confuse newcomers
- **[release-cadence-1]** No releases or version tags found
- **[semver-validation-1]** No git tags found — cannot validate SemVer

## Recommendations

- **[HIGH impact / medium effort]** Add a test suite to improve code reliability and enable coverage tracking
  - https://chaoss.community/metric-test-coverage/
- **[MEDIUM impact / low effort]** Increase scannerTimeout in configuration or check network connectivity
- **[MEDIUM impact / low effort]** Add a LICENSE file with a recognized open source license
- **[MEDIUM impact / low effort]** Increase scannerTimeout in configuration or check network connectivity
- **[MEDIUM impact / low effort]** Add a CODE_OF_CONDUCT.md — see https://www.contributor-covenant.org/
- **[MEDIUM impact / low effort]** Add a SUPPORT.md documenting how users can get help
- **[MEDIUM impact / low effort]** Add sections like "Critical Rules", "Project Structure", "Common Tasks" to improve agent guidance.
- **[MEDIUM impact / low effort]** Increase scannerTimeout in configuration or check network connectivity
- **[MEDIUM impact / low effort]** Increase scannerTimeout in configuration or check network connectivity
- **[MEDIUM impact / low effort]** Check scanner implementation for errors
- **[MEDIUM impact / low effort]** Add .github/ISSUE_TEMPLATE/ with bug report and feature request templates

## Score Rationale

Overall score is a weighted sum of six pillar scores (each scored 0–10).

| Pillar | Weight | Raw Score | Contribution |
|--------|--------|-----------|-------------|
| Security | 25% | 2.0 | 0.50 |
| Governance | 20% | 1.5 | 0.30 |
| Community | 15% | 2.5 | 0.38 |
| AI Readiness | 15% | 2.5 | 0.38 |
| Inclusive Language | 15% | 0.0 | 0.00 |
| Technical Rigor | 10% | 4.5 | 0.45 |
| **Overall** | **100%** | | **2.00** |

---
*quaid-scanner v0.1.2 | 2026-06-01T21:29:31.289Z*
*Commit: 6ef9495d8d5750e5bbb47ca29ae4f81f67aba4aa*