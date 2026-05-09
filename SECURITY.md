# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Quick Capture, please report it by emailing [gabriel.assis.xyz@gmail.com](mailto:gabriel.assis.xyz@gmail.com).

**Do not open a public issue for security vulnerabilities.**

Please include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

I will respond within 48 hours and aim to provide a fix or mitigation within 7 days.

## Security Considerations

- Quick Capture runs via `ai-jail` (bubblewrap sandbox) with restricted filesystem access
- The project reads personal data from the Obsidian vault — be careful with hardcoded paths
- `.env` and `.env.local` files are masked in the jail and should never be committed
- LLM enrichment calls go through `opencode run` subprocess — input is sandboxed