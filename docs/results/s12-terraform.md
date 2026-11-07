# S12: Terraform plans against the live queue ruleset

Terraform 1.17.1, provider `integrations/github` 6.9.0 (installed from a local
filesystem mirror of the release zip), config in [`terraform/`](../../terraform/).
Run on 2026-11-07 against ruleset `main-merge-queue` (id 25550677), after
`terraform import github_repository_ruleset.main_merge_queue merge-queue-lab:25550677`.

| Change planned | Plan |
| --- | --- |
| none (config written to match the live ruleset) | `No changes. Your infrastructure matches the configuration.` |
| `check_response_timeout_minutes` 10 → 11 | `~ update in-place` … `Plan: 0 to add, 1 to change, 0 to destroy.` |
| `name` → `main-merge-queue-renamed` | `~ update in-place` |
| `target` `branch` → `tag` | `~ update in-place` |
| `repository` → another repository | `~ update in-place` |
| resource address renamed (`main_merge_queue` → `queue`), no `moved` block | `github_repository_ruleset.main_merge_queue will be destroyed` / `github_repository_ruleset.queue will be created` … `Plan: 1 to add, 0 to change, 1 to destroy.` |
| the same rename with a `moved { from = … to = … }` block | `has moved to github_repository_ruleset.queue` … `Plan: 0 to add, 0 to change, 0 to destroy.` |

`allowed_merge_methods` inside `pull_request` is rejected by v6.9.0
(`An argument named "allowed_merge_methods" is not expected here.`); the
provider's documentation on its `main` branch already lists it.

`terraform apply` was not run: the session that drove the lab refuses to apply
infrastructure changes without the repository owner's go-ahead.
