#!/usr/bin/env python3
"""Drive the merge queue lab: apply protection models, open scenario PRs, land them, measure.

Everything goes through `gh api` (REST). The only GraphQL use is the optional
`gh pr merge --auto` path for turning on auto-merge, with a REST fallback for
environments where GraphQL is unavailable.

Examples (run from the repository root):
    scripts/lab.py show
    scripts/lab.py apply settings
    scripts/lab.py apply classic --approvals 0          # strict "up to date" baseline
    scripts/lab.py apply queue --timeout 10             # merge queue ruleset on main
    scripts/lab.py apply signed-commits                 # signatures on every branch but gh-pages
    scripts/lab.py open lanes --n 4 --tag s1            # 4 independent PRs
    scripts/lab.py land strict 11 12 13 14              # update-branch / merge loop
    scripts/lab.py land queue 15 16 17 18               # enqueue all, wait
    scripts/lab.py collect 11 12 13 14 --label s1-strict

Repository: taken from --repo, $MQLAB_REPO, or the `origin` remote.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RESULTS = ROOT / "docs" / "results"
GITHUB_ACTIONS_APP_ID = 15368  # the "GitHub Actions" app; pins required checks to it

# --------------------------------------------------------------------------- gh helpers


class GhError(RuntimeError):
    """A gh api call failed."""


def gh(method: str, path: str, body: dict[str, Any] | None = None, *, ok_404: bool = False) -> Any:
    """Call the REST API through gh and return parsed JSON (or None)."""
    cmd = ["gh", "api", "-X", method, "-H", "Accept: application/vnd.github+json", path]
    stdin = None
    if body is not None:
        cmd += ["--input", "-"]
        stdin = json.dumps(body)
    proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        if ok_404 and "HTTP 404" in proc.stderr:
            return None
        raise GhError(f"{method} {path} failed: {proc.stderr.strip()} {proc.stdout.strip()}")
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def detect_repo(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("MQLAB_REPO"):
        return os.environ["MQLAB_REPO"]
    url = subprocess.run(
        ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if not match:
        sys.exit("Cannot work out the repository: pass --repo OWNER/NAME or set MQLAB_REPO.")
    return match.group(1)


# --------------------------------------------------------------------------- configuration


def load(name: str) -> dict[str, Any]:
    return json.loads((CONFIG / name).read_text(encoding="utf-8"))


def find_ruleset(repo: str, name: str) -> dict[str, Any] | None:
    for rs in gh("GET", f"repos/{repo}/rulesets?per_page=100") or []:
        if rs["name"] == name:
            return rs
    return None


def upsert_ruleset(repo: str, body: dict[str, Any]) -> dict[str, Any]:
    existing = find_ruleset(repo, body["name"])
    if existing:
        result = gh("PUT", f"repos/{repo}/rulesets/{existing['id']}", body)
        name, enforcement = body["name"], body["enforcement"]
        log(f"updated ruleset '{name}' (id {existing['id']}, enforcement {enforcement})")
    else:
        result = gh("POST", f"repos/{repo}/rulesets", body)
        name, enforcement = body["name"], body["enforcement"]
        log(f"created ruleset '{name}' (id {result['id']}, enforcement {enforcement})")
    return result


def set_ruleset_enforcement(repo: str, name: str, enforcement: str) -> None:
    existing = find_ruleset(repo, name)
    if not existing:
        return
    full = gh("GET", f"repos/{repo}/rulesets/{existing['id']}")
    body = {
        k: full[k] for k in ("name", "target", "conditions", "rules", "bypass_actors") if k in full
    }
    body["enforcement"] = enforcement
    gh("PUT", f"repos/{repo}/rulesets/{existing['id']}", body)
    log(f"ruleset '{name}' -> {enforcement}")


def required_checks(contexts: list[str]) -> list[dict[str, Any]]:
    return [{"context": c, "integration_id": GITHUB_ACTIONS_APP_ID} for c in contexts]


def apply(args: argparse.Namespace) -> None:
    repo = args.repo
    contexts = ["Required checks", *args.require]
    if args.model == "settings":
        gh("PATCH", f"repos/{repo}", load("repo-settings.json"))
        log(
            "repository merge settings applied (squash only, auto-merge on, delete branch on merge)"
        )
    elif args.model in {"classic", "loose"}:
        set_ruleset_enforcement(repo, "main-merge-queue", "disabled")
        body = load("classic-protection.json")
        body["required_status_checks"]["strict"] = args.model == "classic" and not args.no_strict
        body["required_status_checks"]["checks"] = [
            {"context": c, "app_id": GITHUB_ACTIONS_APP_ID} for c in contexts
        ]
        body["required_pull_request_reviews"]["required_approving_review_count"] = args.approvals
        gh("PUT", f"repos/{repo}/branches/main/protection", body)
        gh("POST", f"repos/{repo}/branches/main/protection/required_signatures")
        log(
            f"classic protection on main: strict={body['required_status_checks']['strict']} "
            f"approvals={args.approvals} checks={contexts} enforce_admins=true signatures=true"
        )
    elif args.model == "queue":
        if gh("GET", f"repos/{repo}/branches/main/protection", ok_404=True):
            gh("DELETE", f"repos/{repo}/branches/main/protection")
            log("removed classic protection on main (the ruleset takes over)")
        body = load("ruleset-main-merge-queue.json")
        for rule in body["rules"]:
            if rule["type"] == "pull_request":
                rule["parameters"]["required_approving_review_count"] = args.approvals
            elif rule["type"] == "required_status_checks":
                rule["parameters"]["required_status_checks"] = required_checks(contexts)
                rule["parameters"]["strict_required_status_checks_policy"] = not args.no_strict
            elif rule["type"] == "merge_queue":
                p = rule["parameters"]
                p["check_response_timeout_minutes"] = args.timeout
                p["grouping_strategy"] = args.grouping
                p["min_entries_to_merge"] = args.min_group
                p["min_entries_to_merge_wait_minutes"] = args.wait
                p["max_entries_to_build"] = args.build
        upsert_ruleset(repo, body)
    elif args.model == "signed-commits":
        body = load("ruleset-signed-commits.json")
        body["enforcement"] = "disabled" if args.off else "active"
        upsert_ruleset(repo, body)
    snapshot(repo, f"config-after-apply-{args.model}")


def snapshot(repo: str, label: str) -> Path:
    """Save the effective protection + rulesets so results can cite them."""
    data = {
        "taken_at": now(),
        "repo_settings": {
            k: v
            for k, v in (gh("GET", f"repos/{repo}") or {}).items()
            if k.startswith(("allow_", "delete_branch", "squash_merge", "merge_commit"))
        },
        "classic_protection": gh("GET", f"repos/{repo}/branches/main/protection", ok_404=True),
        "rulesets": [
            gh("GET", f"repos/{repo}/rulesets/{rs['id']}")
            for rs in gh("GET", f"repos/{repo}/rulesets") or []
        ],
        "rules_on_main": gh("GET", f"repos/{repo}/rules/branches/main"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{label}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"saved {path.relative_to(ROOT)}")
    return path


def show(args: argparse.Namespace) -> None:
    print(json.dumps(json.loads(snapshot(args.repo, "config-current").read_text()), indent=2))


# --------------------------------------------------------------------------- opening PRs

# Files that the semantic-conflict scenario's PR B adds. PR B calls the OLD name
# `apply_discount`, which PR A renames. Each PR is green alone; together they fail.
BASKET_PY = '''"""Basket totals."""

from mqlab.pricing import apply_discount


def basket_total(prices_cents: list[int], percent: int) -> int:
    """Total of all prices after the same discount."""
    return sum(apply_discount(p, percent) for p in prices_cents)
'''

TEST_BASKET_PY = '''"""Unit tests for mqlab.basket."""

from mqlab.basket import basket_total


def test_basket_total_applies_discount_to_each_item() -> None:
    """
    arrange: two prices
    act: total them with 10 percent off
    assert: each item is discounted, then summed
    """
    assert basket_total([1000, 500], 10) == 1350
'''


def main_sha(repo: str) -> str:
    return gh("GET", f"repos/{repo}/git/ref/heads/main")["object"]["sha"]


def create_branch(repo: str, branch: str, sha: str) -> None:
    gh("POST", f"repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})


def put_file(repo: str, branch: str, path: str, text: str, message: str) -> dict[str, Any]:
    """Create or update one file on a branch through the contents API (GitHub signs the commit)."""
    current = gh("GET", f"repos/{repo}/contents/{path}?ref={branch}", ok_404=True)
    body = {
        "message": message,
        "content": base64.b64encode(text.encode()).decode(),
        "branch": branch,
    }
    if current:
        body["sha"] = current["sha"]
    result = gh("PUT", f"repos/{repo}/contents/{path}", body)
    verified = (result["commit"].get("verification") or {}).get("verified")
    log(f"  commit {result['commit']['sha'][:8]} on {branch}: {path} (verified={verified})")
    return result


def read_file(repo: str, path: str, ref: str = "main") -> str:
    data = gh("GET", f"repos/{repo}/contents/{path}?ref={ref}")
    return base64.b64decode(data["content"]).decode()


def open_pr(repo: str, branch: str, title: str, body: str) -> int:
    pr = gh(
        "POST",
        f"repos/{repo}/pulls",
        {"title": title, "head": branch, "base": "main", "body": body},
    )
    log(f"opened PR #{pr['number']}: {title}")
    return pr["number"]


def open_prs(args: argparse.Namespace) -> None:
    repo, tag = args.repo, args.tag
    base = main_sha(repo)
    numbers: list[int] = []
    if args.kind == "lanes":
        for i in range(1, args.n + 1):
            branch = f"lab/{tag}-lane-{i}"
            create_branch(repo, branch, base)
            put_file(
                repo,
                branch,
                f"lanes/lane-{i}.txt",
                f"{tag} lane {i} at {now()}\n",
                f"{tag}: touch lane {i}",
            )
            put_file(
                repo,
                branch,
                f"changes/{tag}-lane-{i}.md",
                f"- {tag}: lane {i} update.\n",
                f"{tag}: changelog for lane {i}",
            )
            numbers.append(
                open_pr(
                    repo,
                    branch,
                    f"{tag}: lane {i}",
                    f"Scenario `{tag}`: independent change {i} of {args.n}.",
                )
            )
    elif args.kind == "conflict":
        source = read_file(repo, "src/mqlab/pricing.py")
        tests = read_file(repo, "tests/unit/test_pricing.py")
        # PR A: rename apply_discount -> discounted_price everywhere it exists today.
        branch_a = f"lab/{tag}-rename"
        create_branch(repo, branch_a, base)
        put_file(
            repo,
            branch_a,
            "src/mqlab/pricing.py",
            source.replace("apply_discount", "discounted_price"),
            f"{tag}: rename apply_discount to discounted_price",
        )
        put_file(
            repo,
            branch_a,
            "tests/unit/test_pricing.py",
            tests.replace("apply_discount", "discounted_price"),
            f"{tag}: follow the rename in tests",
        )
        put_file(
            repo,
            branch_a,
            f"changes/{tag}-rename.md",
            f"- {tag}: rename apply_discount.\n",
            f"{tag}: changelog",
        )
        numbers.append(
            open_pr(
                repo,
                branch_a,
                f"{tag}: rename apply_discount to discounted_price",
                "Scenario semantic conflict, PR A. Green on its own.",
            )
        )
        # PR B: add a new caller of the OLD name, plus a test for it.
        branch_b = f"lab/{tag}-new-caller"
        create_branch(repo, branch_b, base)
        put_file(
            repo,
            branch_b,
            "src/mqlab/basket.py",
            BASKET_PY,
            f"{tag}: add basket_total using apply_discount",
        )
        put_file(
            repo,
            branch_b,
            "tests/unit/test_basket.py",
            TEST_BASKET_PY,
            f"{tag}: test basket_total",
        )
        put_file(
            repo,
            branch_b,
            f"changes/{tag}-basket.md",
            f"- {tag}: add basket_total.\n",
            f"{tag}: changelog",
        )
        numbers.append(
            open_pr(
                repo,
                branch_b,
                f"{tag}: add basket_total (calls apply_discount)",
                "Scenario semantic conflict, PR B. Green on its own; broken once PR A lands.",
            )
        )
    print(json.dumps({"opened": numbers}))


# --------------------------------------------------------------------------- landing PRs


def pr(repo: str, number: int) -> dict[str, Any]:
    return gh("GET", f"repos/{repo}/pulls/{number}")


def wait_mergeable_state(repo: str, number: int, timeout_s: int) -> dict[str, Any]:
    """Poll until GitHub has computed a mergeable_state other than unknown/blocked-pending."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        p = pr(repo, number)
        if p["merged"] or p["state"] == "closed":
            return p
        state = p.get("mergeable_state")
        if state in {"clean", "behind", "dirty", "unstable", "has_hooks"}:
            return p
        if state == "blocked":
            # Blocked can mean "checks still running" or "requirements failed". Look at the checks.
            runs = gh("GET", f"repos/{repo}/commits/{p['head']['sha']}/check-runs?per_page=100")[
                "check_runs"
            ]
            req = [r for r in runs if r["name"] == "Required checks"]
            if req and req[0]["status"] == "completed" and req[0]["conclusion"] != "success":
                return p
        time.sleep(15)
    raise TimeoutError(f"PR #{number} did not settle within {timeout_s}s")


def land_strict(repo: str, numbers: list[int], timeout_s: int) -> dict[str, Any]:
    """Classic strict protection: for each PR, update branch while behind, then merge."""
    actions: list[dict[str, Any]] = []
    for number in numbers:
        while True:
            p = wait_mergeable_state(repo, number, timeout_s)
            state = p["mergeable_state"]
            if p["merged"]:
                break
            if state == "behind":
                gh(
                    "PUT",
                    f"repos/{repo}/pulls/{number}/update-branch",
                    {"expected_head_sha": p["head"]["sha"]},
                )
                actions.append({"at": now(), "pr": number, "action": "update-branch"})
                log(f"#{number} behind main -> update-branch (CI restarts)")
                time.sleep(20)
                continue
            if state == "clean":
                gh(
                    "PUT",
                    f"repos/{repo}/pulls/{number}/merge",
                    {"merge_method": "squash", "sha": p["head"]["sha"]},
                )
                actions.append({"at": now(), "pr": number, "action": "merge"})
                log(f"#{number} merged")
                break
            actions.append({"at": now(), "pr": number, "action": f"stopped:{state}"})
            log(f"#{number} cannot merge (mergeable_state={state}); leaving it")
            break
    return {"model": "strict", "actions": actions}


def enqueue(repo: str, number: int, via: str) -> str:
    """Put a PR on the path to the merge queue.

    via="async": REST `PUT /pulls/{n}/merge-async` with merge_action=merge_queue (GA 2026-10-01).
    via="auto":  `gh pr merge --auto` (GraphQL), i.e. "Merge when ready"; falls back to a REST
                 auto-merge route that some sandboxes expose when GraphQL is unavailable.
    """
    if via == "async":
        result = gh(
            "PUT", f"repos/{repo}/pulls/{number}/merge-async", {"merge_action": "merge_queue"}
        )
        return f"merge-async -> {json.dumps(result, sort_keys=True)}"
    proc = subprocess.run(
        ["gh", "pr", "merge", str(number), "--repo", repo, "--auto", "--squash"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return (proc.stdout + proc.stderr).strip() or "gh pr merge --auto ok"
    if "graphql" not in proc.stderr.lower():
        raise GhError(proc.stderr.strip())
    gh("PUT", f"repos/{repo}/pulls/{number}/ccr/auto_merge", {"merge_method": "SQUASH"})
    return "auto-merge enabled via REST fallback"


def land_queue(repo: str, numbers: list[int], timeout_s: int, via: str = "async") -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for number in numbers:
        msg = enqueue(repo, number, via)
        actions.append({"at": now(), "pr": number, "action": f"enqueue ({via})", "detail": msg})
        log(f"#{number}: {msg}")
    pending = set(numbers)
    deadline = time.time() + timeout_s
    while pending and time.time() < deadline:
        for number in sorted(pending):
            p = pr(repo, number)
            if p["merged"]:
                actions.append({"at": now(), "pr": number, "action": "merged-by-queue"})
                log(f"#{number} merged by the queue")
                pending.discard(number)
            elif queue_removed(repo, number):
                actions.append({"at": now(), "pr": number, "action": "removed-from-queue"})
                log(f"#{number} was removed from the queue without merging")
                pending.discard(number)
        time.sleep(20)
    for number in pending:
        actions.append({"at": now(), "pr": number, "action": "timeout-waiting"})
    return {"model": "queue", "actions": actions}


def queue_removed(repo: str, number: int) -> bool:
    events = timeline(repo, number)
    added = [e for e in events if e.get("event") == "added_to_merge_queue"]
    removed = [e for e in events if e.get("event") == "removed_from_merge_queue"]
    return bool(added) and len(removed) >= len(added)


def land(args: argparse.Namespace) -> None:
    started = now()
    if args.model == "strict":
        result = land_strict(args.repo, args.prs, args.timeout)
    else:
        result = land_queue(args.repo, args.prs, args.timeout, args.via)
    result.update({"started": started, "finished": now(), "prs": args.prs})
    print(json.dumps(result, indent=2))
    if args.label:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / f"{args.label}-actions.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )


# --------------------------------------------------------------------------- measuring


def timeline(repo: str, number: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = gh("GET", f"repos/{repo}/issues/{number}/timeline?per_page=100&page={page}") or []
        items.extend(batch)
        if len(batch) < 100:
            break
    return items


def runs_for(
    repo: str, *, branch: str | None = None, event: str | None = None
) -> list[dict[str, Any]]:
    query = "per_page=100"
    if branch:
        query += f"&branch={branch}"
    if event:
        query += f"&event={event}"
    out: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = (gh("GET", f"repos/{repo}/actions/runs?{query}&page={page}") or {}).get(
            "workflow_runs", []
        )
        out.extend(batch)
        if len(batch) < 100:
            break
    return out


def minutes(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    t = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return round((t(b) - t(a)).total_seconds() / 60, 1)


def collect(args: argparse.Namespace) -> None:
    repo = args.repo
    merge_group_runs = runs_for(repo, event="merge_group")
    rows = []
    for number in args.prs:
        p = pr(repo, number)
        events = timeline(repo, number)
        pr_runs = runs_for(repo, branch=p["head"]["ref"], event="pull_request")
        mg_runs = [
            r
            for r in merge_group_runs
            if r["head_branch"].startswith(f"gh-readonly-queue/main/pr-{number}-")
        ]
        rows.append(
            {
                "pr": number,
                "title": p["title"],
                "url": p["html_url"],
                "author": p["user"]["login"],
                "created_at": p["created_at"],
                "merged_at": p["merged_at"],
                "merged_by": (p.get("merged_by") or {}).get("login"),
                "state": "merged" if p["merged"] else p["state"],
                "queue_adds": sum(1 for e in events if e.get("event") == "added_to_merge_queue"),
                "queue_removals": sum(
                    1 for e in events if e.get("event") == "removed_from_merge_queue"
                ),
                "update_branch_commits": sum(
                    1
                    for e in events
                    if e.get("event") == "committed"
                    and (e.get("message") or "").startswith("Merge branch 'main'")
                ),
                "pull_request_runs": len(pr_runs),
                "merge_group_runs": len(mg_runs),
                "ci_minutes": round(
                    sum(
                        minutes(r.get("run_started_at"), r.get("updated_at")) or 0
                        for r in pr_runs + mg_runs
                    ),
                    1,
                ),
                "events": [
                    {
                        "event": e.get("event"),
                        "actor": (e.get("actor") or {}).get("login"),
                        "at": e.get("created_at"),
                    }
                    for e in events
                    if e.get("event")
                    in {
                        "added_to_merge_queue",
                        "removed_from_merge_queue",
                        "auto_merge_enabled",
                        "auto_squash_enabled",
                        "merged",
                        "head_ref_force_pushed",
                        "reviewed",
                    }
                ],
            }
        )
    merged = [r["merged_at"] for r in rows if r["merged_at"]]
    summary = {
        "label": args.label,
        "collected_at": now(),
        "prs": len(rows),
        "merged": len(merged),
        "first_pr_created": min(r["created_at"] for r in rows),
        "last_merge": max(merged) if merged else None,
        "wall_minutes_first_open_to_last_merge": minutes(
            min(r["created_at"] for r in rows), max(merged)
        )
        if merged
        else None,
        "total_ci_runs": sum(r["pull_request_runs"] + r["merge_group_runs"] for r in rows),
        "total_ci_minutes": round(sum(r["ci_minutes"] for r in rows), 1),
        "rows": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{args.label}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log(f"saved {path.relative_to(ROOT)}")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))


# --------------------------------------------------------------------------- probing merge paths


def probe(args: argparse.Namespace) -> None:
    """Attempt one merge path against a PR and record GitHub's literal answer."""
    repo, number = args.repo, args.pr
    head = pr(repo, number)["head"]["sha"]
    calls = {
        "rest-merge": (
            "PUT",
            f"repos/{repo}/pulls/{number}/merge",
            {"merge_method": "squash", "sha": head},
        ),
        "async-direct": (
            "PUT",
            f"repos/{repo}/pulls/{number}/merge-async",
            {"merge_action": "direct_merge"},
        ),
        "async-direct-bypass": (
            "PUT",
            f"repos/{repo}/pulls/{number}/merge-async",
            {"merge_action": "direct_merge", "bypass_rules": True},
        ),
        "async-queue": (
            "PUT",
            f"repos/{repo}/pulls/{number}/merge-async",
            {"merge_action": "merge_queue"},
        ),
        "update-branch": (
            "PUT",
            f"repos/{repo}/pulls/{number}/update-branch",
            {"expected_head_sha": head},
        ),
    }
    method, path, body = calls[args.path]
    outcome: dict[str, Any] = {
        "at": now(),
        "pr": number,
        "probe": args.path,
        "request": {"method": method, "path": path, "body": body},
    }
    try:
        outcome["response"] = gh(method, path, body)
        outcome["ok"] = True
    except GhError as err:
        outcome["ok"] = False
        outcome["error"] = str(err)
    print(json.dumps(outcome, indent=2))
    if args.label:
        RESULTS.mkdir(parents=True, exist_ok=True)
        path_out = RESULTS / f"{args.label}-probes.json"
        existing = json.loads(path_out.read_text()) if path_out.exists() else []
        existing.append(outcome)
        path_out.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- CLI


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", help="OWNER/NAME (default: $MQLAB_REPO or the origin remote)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show", help="print and save the current protection and rulesets")

    p_apply = sub.add_parser("apply", help="apply a protection model")
    p_apply.add_argument(
        "model", choices=["settings", "classic", "loose", "queue", "signed-commits"]
    )
    p_apply.add_argument("--approvals", type=int, default=0)
    p_apply.add_argument(
        "--require", action="append", default=[], help="extra required check name (repeatable)"
    )
    p_apply.add_argument(
        "--no-strict", action="store_true", help="do not require branches to be up to date"
    )
    p_apply.add_argument("--timeout", type=int, default=10, help="queue check timeout, minutes")
    p_apply.add_argument("--grouping", choices=["ALLGREEN", "HEADGREEN"], default="ALLGREEN")
    p_apply.add_argument("--min-group", type=int, default=1)
    p_apply.add_argument("--wait", type=int, default=0, help="minutes to wait for min group size")
    p_apply.add_argument("--build", type=int, default=5, help="max entries to build concurrently")
    p_apply.add_argument(
        "--off", action="store_true", help="for signed-commits: disable instead of enable"
    )

    p_open = sub.add_parser("open", help="open scenario pull requests")
    p_open.add_argument("kind", choices=["lanes", "conflict"])
    p_open.add_argument("--n", type=int, default=4)
    p_open.add_argument("--tag", required=True, help="scenario tag used in branch names, e.g. s1")

    p_land = sub.add_parser("land", help="land pull requests under a model and record the steps")
    p_land.add_argument("model", choices=["strict", "queue"])
    p_land.add_argument("prs", type=int, nargs="+")
    p_land.add_argument("--timeout", type=int, default=3600, help="seconds")
    p_land.add_argument(
        "--via", choices=["async", "auto"], default="async", help="how to enqueue (queue model)"
    )
    p_land.add_argument("--label", help="save the action log as docs/results/<label>-actions.json")

    p_probe = sub.add_parser(
        "probe", help="try a merge path and record exactly what GitHub answers"
    )
    p_probe.add_argument(
        "path",
        choices=[
            "rest-merge",
            "async-direct",
            "async-direct-bypass",
            "async-queue",
            "update-branch",
        ],
    )
    p_probe.add_argument("pr", type=int)
    p_probe.add_argument("--label", help="append the outcome to docs/results/<label>-probes.json")

    p_collect = sub.add_parser("collect", help="measure finished pull requests")
    p_collect.add_argument("prs", type=int, nargs="+")
    p_collect.add_argument("--label", required=True)

    args = parser.parse_args()
    args.repo = detect_repo(args.repo)
    {
        "show": show,
        "apply": apply,
        "open": open_prs,
        "land": land,
        "collect": collect,
        "probe": probe,
    }[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
