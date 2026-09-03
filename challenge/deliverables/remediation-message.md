Hey Tinus Lorvalds,

Just finished my security review of the records API. A few issues need your team's urgent attention. The first three let any logged-in member read other members' health records; the fourth is internal network exposure.

- IDOR on `GET /api/records/{id}` (app/routes/records.py:27). No owner check. `/notes` already does it right, copy that pattern. ~1 hour.
- `GET /api/search` returns every user's records (app/routes/search.py:17). An empty query dumps all of them.
- SQL injection in search (app/db.py:78). Parameterize the query. The global error handler echoes `repr(exc)` (app/main.py:26), which makes this worse; return a generic 500.
- SSRF in the vendor-preview webhook (app/routes/webhooks.py:25). Staff-only, but it reaches the internal network and returns the response body. Allowlist vendor hosts and drop the body.

There are two additional issues involving token security that we will also need to get fixed within the next 2 sprints, but ideally right away as well if you guys have the bandwidth.

These come with major compliance risks, legal implications, reputational damage, and business critical systems impact, so the business is going to need these fixed unfortunately as soon as possible, hopefully we can do a hotfix. Let's hop on a call when you have time and discuss, I'll help your team however I can to get these resolved
