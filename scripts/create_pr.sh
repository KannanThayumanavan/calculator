#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# create_pr.sh
# Creates a pull request against the repository's default base branch.
# Jira: TEST-1
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Resolve REPO (owner/name)
# ---------------------------------------------------------------------------
if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
  REPO="${GITHUB_REPOSITORY}"
else
  echo "GITHUB_REPOSITORY not set – falling back to 'gh repo view'..."
  REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
fi

if [[ -z "${REPO:-}" ]]; then
  echo "ERROR: Could not determine repository name. " \
       "Set GITHUB_REPOSITORY or ensure 'gh' is authenticated." >&2
  exit 1
fi

echo "Resolved repository: ${REPO}"

# ---------------------------------------------------------------------------
# Resolve BASE_BRANCH dynamically from the GitHub API
# ---------------------------------------------------------------------------
BASE_BRANCH="$(gh api "repos/${REPO}" --jq '.default_branch')"

if [[ -z "${BASE_BRANCH:-}" ]]; then
  echo "ERROR: Could not determine the default branch for '${REPO}'. " \
       "Verify that the GitHub token has 'repo' (or 'metadata:read') scope " \
       "and that the repository exists." >&2
  exit 1
fi

echo "Resolved base branch: ${BASE_BRANCH}"

# ---------------------------------------------------------------------------
# Configurable PR parameters (override via environment variables)
# ---------------------------------------------------------------------------
PR_TITLE="${PR_TITLE:-"Automated PR – $(date -u +'%Y-%m-%d %H:%M UTC')"}"
PR_BODY="${PR_BODY:-"This pull request was created automatically by the SDLC pipeline.\n\nJira: TEST-1"}"
PR_DRAFT="${PR_DRAFT:-"false"}"

# The head branch is the currently checked-out branch unless overridden.
HEAD_BRANCH="${HEAD_BRANCH:-"$(git rev-parse --abbrev-ref HEAD)"}"

if [[ -z "${HEAD_BRANCH:-}" || "${HEAD_BRANCH}" == "HEAD" ]]; then
  echo "ERROR: Could not determine the head (source) branch. " \
       "Ensure the workspace has a checked-out branch, or set HEAD_BRANCH." >&2
  exit 1
fi

echo "Head branch  : ${HEAD_BRANCH}"
echo "Base branch  : ${BASE_BRANCH}"
echo "Repository   : ${REPO}"
echo "PR title     : ${PR_TITLE}"
echo "Draft        : ${PR_DRAFT}"

# ---------------------------------------------------------------------------
# Guard: do not open a PR from a branch onto itself
# ---------------------------------------------------------------------------
if [[ "${HEAD_BRANCH}" == "${BASE_BRANCH}" ]]; then
  echo "ERROR: HEAD_BRANCH and BASE_BRANCH are both '${BASE_BRANCH}'. " \
       "Cannot create a PR from a branch onto itself." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Create the pull request
# ---------------------------------------------------------------------------
DRAFT_FLAG=""
if [[ "${PR_DRAFT}" == "true" ]]; then
  DRAFT_FLAG="--draft"
fi

echo "Creating pull request..."

PR_URL="$(gh pr create \
  --repo    "${REPO}" \
  --base    "${BASE_BRANCH}" \
  --head    "${HEAD_BRANCH}" \
  --title   "${PR_TITLE}" \
  --body    "$(printf '%b' "${PR_BODY}")" \
  ${DRAFT_FLAG})"

echo "Pull request created successfully: ${PR_URL}"