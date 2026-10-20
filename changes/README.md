# Changelog fragments

Every human pull request adds one small Markdown file here, for example
`changes/123-short-title.md`. The **Changelog** workflow checks for it.

That check exists in this lab because it is a very common *pull-request-shaped*
check: it reads the pull request's base and head commits. Inside a merge queue
there is no pull request object, so such checks need care. See
[docs/scenarios.md](../docs/scenarios.md), scenarios S5 and S6.

Pull requests opened by bots (author type `Bot`) are exempt, which mirrors how
many teams treat dependency updates.
