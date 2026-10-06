# Security policy

DODGE publishes a public dataset and a static website. People may rely on its numbers, so its integrity is part of its security. Please report anything that could let someone change what DODGE publishes, run code in a visitor's browser, or misuse the project's credentials.

## Reporting a vulnerability

**Please do not open a public issue.**

* Preferred: [report privately through GitHub](https://github.com/GautamTalksDev/dodge/security/advisories/new) (Security tab, "Report a vulnerability").
* Or email developwith.gt@gmail.com with "DODGE security" in the subject.

Include what you found, how to reproduce it, and what an attacker could do with it.

## What to expect

| Step | Target |
|---|---|
| Acknowledgement | within 3 days |
| First assessment | within 7 days |
| Fix or mitigation for high or critical issues | within 30 days |
| Public advisory and credit (if you want it) | when the fix ships |

DODGE is maintained by one person, so these are best-effort targets, but they are taken seriously.

## In scope

* The website at `dodge.gautamkhosla.com`: cross-site scripting, header or policy weaknesses, anything that runs code in a visitor's browser.
* The GitHub Actions workflows: injection, token or permission misuse, anything that could alter published data or releases.
* Data integrity: a way to make a published file, manifest or attestation appear genuine when it is not, or to break the daily hash chain without detection.
* The Python engine and recorder, where a crafted input could cause code execution.

## Out of scope

* The accuracy of public orbit data. That is a data question: open a "Data correction" issue instead.
* CelesTrak, GitHub, Cloudflare and Sigstore themselves. Report those to their owners.
* Denial of service, rate limits, and findings from automated scanners without a demonstrated impact.
* Missing security headers that are present, or that have no effect on a static site.

## Safe harbour

Good-faith research that respects this policy is welcome. Do not access data that is not yours, do not degrade the service for others, and give a reasonable time to fix before you publish. If you follow these rules, the maintainer will not pursue or support legal action against you.

## How DODGE is protected

The controls, and why each exists, are listed in [docs/SECURITY_PRACTICES.md](docs/SECURITY_PRACTICES.md). The threat model is in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md). To check that published data is genuine, see [docs/VERIFYING.md](docs/VERIFYING.md).
