# Scenario S12: the lab's merge-queue ruleset as Terraform.
#
# Manages ONLY the existing "main-merge-queue" ruleset of this repository. Import it
# first, so Terraform never creates a second queue on main:
#
#   terraform init
#   terraform import github_repository_ruleset.main_merge_queue merge-queue-lab:<ruleset id>
#   terraform plan -var timeout=11
#
# The provider reads its token from GITHUB_TOKEN and the owner from GITHUB_OWNER
# (or the `owner` variable below).

terraform {
  required_version = ">= 1.5"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "6.9.0" # merge_queue first appears in v6.6.0
    }
  }
}

variable "owner" {
  type    = string
  default = "minulo-lab"
}

variable "ruleset_name" {
  type    = string
  default = "main-merge-queue"
}

variable "timeout" {
  description = "Merge queue: minutes a required check may stay silent"
  type        = number
  default     = 10
}

provider "github" {
  owner = var.owner
}

resource "github_repository_ruleset" "main_merge_queue" {
  name        = var.ruleset_name
  repository  = "merge-queue-lab"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  rules {
    deletion         = true
    non_fast_forward = true

    pull_request {
      required_approving_review_count   = 0
      dismiss_stale_reviews_on_push     = false
      require_code_owner_review         = false
      require_last_push_approval        = false
      required_review_thread_resolution = false
      # allowed_merge_methods: not in provider v6.9.0 (only in later docs), so it cannot be set here
    }

    required_status_checks {
      strict_required_status_checks_policy = true
      do_not_enforce_on_create             = false
      required_check {
        context        = "Required checks"
        integration_id = 15368
      }
    }

    # Set every field: several provider defaults differ from what this lab uses
    # (merge_method MERGE, timeout 60, wait 5).
    merge_queue {
      merge_method                      = "SQUASH"
      grouping_strategy                 = "ALLGREEN"
      max_entries_to_build              = 5
      min_entries_to_merge              = 1
      max_entries_to_merge              = 5
      min_entries_to_merge_wait_minutes = 0
      check_response_timeout_minutes    = var.timeout
    }
  }
}

output "ruleset_id" {
  value = github_repository_ruleset.main_merge_queue.ruleset_id
}
