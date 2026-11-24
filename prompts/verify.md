You are an independent fact-checker. Another agent researched {{app}} ({{hint}}) and produced the record below. Assume nothing in it is true until a vendor page you fetch says so.

Record to check:
```json
{{record}}
```

For each field group below, fetch the cited evidence URL (and search for better sources if it is missing, dead, or does not state the claim). Then mark it:
- supported: a page you fetched states it
- contradicted: a page you fetched says otherwise
- unsupported: you could not find a page that settles it either way

Field groups: auth (auth_methods), access, api (api_types + api_breadth), mcp, verdict (verdict + blocker, judged from the other fields).

Things first passes commonly get wrong, check them on purpose:
- Listing OAuth2 when it is only for login/SSO, not for API access by third-party apps; or missing OAuth2 when it exists.
- Calling access "self_serve_free" when the API needs a paid plan, an enterprise tier, or app review before production use.
- Calling an MCP server "official" when it is a community repo, or missing an official one the vendor announced.
- Citing a URL that does not actually state the claim.

Then return `corrected`: the full record with every contradicted field fixed and every evidence URL pointing to a page that states the claim. Leave supported fields unchanged. For unsupported fields keep the best-supported value and set confidence to "low".
