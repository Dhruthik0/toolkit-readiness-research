You are researching one app to decide whether it can become an AI-agent toolkit (a set of API actions an agent can call on a user's behalf).

App: {{app}}
Hint: {{hint}}

Use WebSearch and WebFetch. Prefer the vendor's own developer docs over blogs, and fetch the page before you cite it. Every evidence URL must be a page you actually fetched that states the claim.

Answer these:
1. category and one_liner: what the product is, in one sentence.
2. auth_methods: how a third-party integration authenticates to the API. List every supported method. "Bearer token" means a static token such as a personal access token; "API key" means a key sent in a header or query string; OAuth2 only if the vendor documents an OAuth flow for third-party apps.
3. access: the cheapest way a developer gets working credentials.
   - self_serve_free: free account or free developer/sandbox account gives API access
   - self_serve_trial: only through a time-limited free trial
   - paid_plan: API needs a paid tier (say which in access_notes)
   - approval_required: credentials exist but need vendor review/app approval before real use (e.g. app review, production access request)
   - partner_gated: need a partnership, enterprise contract or contact-sales to get any API access
   - no_public_api: no documented public API
4. api_types and api_breadth: what is documented publicly.
5. mcp: is there an official MCP server from the vendor (official), only third-party ones (community), or none you could find (none_found). Give its URL.
6. verdict and blocker:
   - ready: self-serve credentials + documented API, an agent toolkit could be built today
   - ready_with_caveats: buildable, but something limits it (paid tier, app review for production, narrow API, rate limits, ToS)
   - blocked: cannot build without outreach or no API (state the blocker)
7. confidence: high only if every field is backed by a fetched vendor page.

If something is unclear or you cannot find it, say so in the notes and lower confidence. Do not guess.
