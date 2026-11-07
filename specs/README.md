# AI Advisory product specifications

**Version 2.1 · 2026-11-05 · Planning backlog only. No implementation is authorized by these documents.**

This roadmap expands the original 23-document/45-task handoff into a product plan. The historical application baseline is `818b219`; no fresh app/code security review was performed for this specification update. Requirements are proposed behavior, not existing functionality. The user will decide which release to implement and when.

## Start here
1. [Product vision and release scope](product-vision.md) — plain-language product goal and phased delivery.
2. [Market comparison](market-comparison.md) — sourced capability comparison and resulting gaps.
3. [Release gates and open decisions](release-gates.md) — prerequisites, choices and proof needed to launch.
4. [Financial rules](financial-rules.md) — definitions and exact examples shared by every agent.
5. [Architecture](architecture.md), [constitution](constitution.md) and [agent role map](agent-role-map.md).
6. [Agent quality](agent-quality.md), [evaluation plan](evaluation-plan.md), [review checklist](review-checklist.md) and [compliance register](compliance-register.md).
7. [Implementation order](implementation-order.md), [coverage and task index](coverage-index.md) and [change log](CHANGELOG.md).

## Feature packages
| ID | Specification | Delivery documents |
|---|---|---|
| 001 | [Reliable analysis and account safety](001-reliable-foundation/spec.md) | [Plan](001-reliable-foundation/plan.md) · [Tasks](001-reliable-foundation/tasks.md) |
| 002 | [Monthly Finance Agent](002-monthly-finance/spec.md) | [Plan](002-monthly-finance/plan.md) · [Tasks](002-monthly-finance/tasks.md) |
| 003 | [Portfolio tracking and risk](003-portfolio-risk/spec.md) | [Plan](003-portfolio-risk/plan.md) · [Tasks](003-portfolio-risk/tasks.md) |
| 004 | [Tax preparation agent](004-tax-preparation/spec.md) | [Plan](004-tax-preparation/plan.md) · [Tasks](004-tax-preparation/tasks.md) |
| 005 | [Credit tracking and external integrations](005-external-integrations/spec.md) | [Plan](005-external-integrations/plan.md) · [Tasks](005-external-integrations/tasks.md) |
| 006 | [Budgets, recurring bills, goals and debt planning](006-budgets-goals-debt/spec.md) | [Plan](006-budgets-goals-debt/plan.md) · [Tasks](006-budgets-goals-debt/tasks.md) |
| 007 | [Personalized allocation and portfolio optimization](007-personalized-allocation/spec.md) | [Plan](007-personalized-allocation/plan.md) · [Tasks](007-personalized-allocation/tasks.md) |
| 008 | [Privacy, consent and account lifecycle](008-privacy-account-lifecycle/spec.md) | [Plan](008-privacy-account-lifecycle/plan.md) · [Tasks](008-privacy-account-lifecycle/tasks.md) |
| 009 | [Production reliability, deployment and cost controls](009-production-operations/spec.md) | [Plan](009-production-operations/plan.md) · [Tasks](009-production-operations/tasks.md) |
| 010 | [Onboarding, responsive UI, accessibility and notifications](010-product-experience/spec.md) | [Plan](010-product-experience/plan.md) · [Tasks](010-product-experience/tasks.md) |
| 011 | [Household net worth and protection inventory](011-household-networth-protection/spec.md) | [Plan](011-household-networth-protection/plan.md) · [Tasks](011-household-networth-protection/tasks.md) |
| 012 | [Financial education, evidence retrieval and research agents](012-knowledge-research/spec.md) | [Plan](012-knowledge-research/plan.md) · [Tasks](012-knowledge-research/tasks.md) |
| 013 | [Commercial readiness, subscriptions and customer support](013-commercial-support/spec.md) | [Plan](013-commercial-support/plan.md) · [Tasks](013-commercial-support/tasks.md) |
| 014 | [Document coverage, OCR and transaction corrections](014-document-coverage/spec.md) | [Plan](014-document-coverage/plan.md) · [Tasks](014-document-coverage/tasks.md) |

## How to use with Claude and Codex
Wait for the user to select a feature/release. Read its spec, plan and tasks plus the shared documents. Resolve prerequisite decisions for that slice. Preserve current application data and working entry points; do not rewrite the stack merely because a new framework exists. Implement small changes and attach requirement-to-test evidence. Codex reviews the implementation commit range, migrations, browser paths and actual results against the chosen scope. Neither agent may mark unrun checks as passing. No application work should start just because this folder exists.

Each feature has one current requirements list. Task IDs remain stable; use [implementation order](implementation-order.md) for dependencies and shared ownership. Number order is a capability index: 008 privacy, 009 operations and 010 core UX must accompany the early pilot. Do not defer them until after live integrations. Plans describe module boundaries; actual schemas/OpenAPI and deployment parameters are pinned during the selected slice.

## Spec Kit usage
These documents follow the [GitHub Spec Kit](https://github.com/github/spec-kit) specification/plan/tasks approach: user stories, requirements, implementation constraints and verifiable tasks. The Specify CLI and agent slash-command integration are **not installed by this update**. This is a manually authored Spec Kit-aligned roadmap, not a claim that CLI-generated project setup exists. Installing or initializing tooling can be a separate selected action without overwriting this work.

## Scope boundaries
The full roadmap covers personal finance automation, not all finance jobs. Some provider, advice, research and filing capabilities remain independently gated. Optional paid plans, household sharing, OCR and research are not mandatory for the first pilot. No real customer data, trades, filings, subscriptions or messages are created by these specs.

Every feature also includes `acceptance.md` mapping each requirement to task IDs and concrete acceptance cases. These are planned tests, not passing test reports.
