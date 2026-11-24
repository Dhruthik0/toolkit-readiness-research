A fact-checker could not confirm how a developer gets API access to {{app}} ({{hint}}), or what API it has. Often that is because the docs pages are JavaScript-rendered and did not load. Settle it.

Current record:
```json
{{record}}
```

Find the vendor's OWN developer documentation. If a page does not render, try in order: `<docs-site>/llms.txt`, the `.md` version of the page, the vendor's GitHub org (OpenAPI specs, SDK READMEs), the vendor's help center, then search results restricted to the vendor's domain. Third-party integration sites (Zapier, n8n, Nango, emergent.sh and similar) are not evidence of access terms.

Then answer:
- vendor_docs_url: the vendor developer/API docs page you reached, or null if none exists
- access: same enum as before. Use no_public_api only if the vendor publishes no developer docs at all; use partner_gated if API access is only via sales/enterprise onboarding.
- api_types: what the vendor docs show
- evidence_quote: a short quote from a vendor page that settles access
- notes
