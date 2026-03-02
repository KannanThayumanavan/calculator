import pytest
import yaml
import os
import re


WORKFLOW_FILE_PATHS = [
    ".github/workflows/sdlc-pipeline.yml",
    ".github/workflows/sdlc_pipeline.yml",
    ".github/workflows/pipeline.yml",
    ".github/workflows/main.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/cd.yml",
    ".github/workflows/pr.yml",
]

STEP_NAME_PATTERNS = [
    re.compile(r"create\s+pull\s+request", re.IGNORECASE),
    re.compile(r"open\s+pull\s+request", re.IGNORECASE),
    re.compile(r"make\s+pull\s+request", re.IGNORECASE),
    re.compile(r"pr\s+creation", re.IGNORECASE),
    re.compile(r"create[_\-]pr", re.IGNORECASE),
    re.compile(r"open[_\-]pr", re.IGNORECASE),
]

DYNAMIC_BRANCH_OUTPUT_PATTERNS = [
    re.compile(r"steps\.default[_\-]branch\.outputs\.branch", re.IGNORECASE),
    re.compile(r"\$\{\{\s*steps\.default[_\-]branch\.outputs\.branch\s*\}\}"),
    re.compile(r"steps\[.default.?branch.\]\.outputs\.branch", re.IGNORECASE),
]

HARDCODED_BRANCH_PATTERNS = [
    re.compile(r"(?<!['\"\w])master(?!['\"\w])", re.IGNORECASE),
    re.compile(r"(?<!['\"\w])main(?!['\"\w])", re.IGNORECASE),
]

DESTINATION_BRANCH_KEYS = [
    "destination_branch",
    "base",
    "base_branch",
    "target_branch",
    "head_branch",
]


def find_workflow_file():
    repo_root_candidates = [
        os.getcwd(),
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "/workspace",
        "/app",
        "/repo",
    ]

    for root in repo_root_candidates:
        for rel_path in WORKFLOW_FILE_PATHS:
            full_path = os.path.join(root, rel_path)
            if os.path.isfile(full_path):
                return full_path

    # Search recursively from cwd
    for dirpath, dirnames, filenames in os.walk(os.getcwd()):
        # Skip hidden dirs except .github
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") or d == ".github"
        ]
        for filename in filenames:
            if filename.endswith(".yml") or filename.endswith(".yaml"):
                full_path = os.path.join(dirpath, filename)
                if ".github/workflows" in full_path.replace("\\", "/"):
                    return full_path

    return None


def load_workflow_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    data = yaml.safe_load(content)
    return data, content


def is_create_pr_step(step):
    if not isinstance(step, dict):
        return False
    step_name = step.get("name", "")
    if isinstance(step_name, str):
        for pattern in STEP_NAME_PATTERNS:
            if pattern.search(step_name):
                return True
    # Check uses field
    uses = step.get("uses", "")
    if isinstance(uses, str):
        pr_uses_patterns = [
            re.compile(r"create-pull-request", re.IGNORECASE),
            re.compile(r"pull-request", re.IGNORECASE),
            re.compile(r"gh-action-pr", re.IGNORECASE),
            re.compile(r"peter-evans/create-pull-request", re.IGNORECASE),
            re.compile(r"repo-sync/pull-request", re.IGNORECASE),
        ]
        for pattern in pr_uses_patterns:
            if pattern.search(uses):
                return True
    # Check run field for gh pr create or hub pull-request
    run = step.get("run", "")
    if isinstance(run, str):
        run_patterns = [
            re.compile(r"gh\s+pr\s+create", re.IGNORECASE),
            re.compile(r"hub\s+pull-request", re.IGNORECASE),
            re.compile(r"curl.*pulls", re.IGNORECASE),
            re.compile(r"api.*pulls", re.IGNORECASE),
        ]
        for pattern in run_patterns:
            if pattern.search(run):
                return True
    return False


def extract_all_steps(workflow_data):
    steps = []
    if not isinstance(workflow_data, dict):
        return steps
    jobs = workflow_data.get("jobs", {})
    if not isinstance(jobs, dict):
        return steps
    for job_name, job_data in jobs.items():
        if not isinstance(job_data, dict):
            continue
        job_steps = job_data.get("steps", [])
        if not isinstance(job_steps, list):
            continue
        for step in job_steps:
            steps.append((job_name, step))
    return steps


def extract_pr_steps(workflow_data):
    all_steps = extract_all_steps(workflow_data)
    pr_steps = []
    for job_name, step in all_steps:
        if is_create_pr_step(step):
            pr_steps.append((job_name, step))
    return pr_steps


def get_destination_branch_value(step):
    if not isinstance(step, dict):
        return None

    # Check 'with' block for action inputs
    with_block = step.get("with", {})
    if isinstance(with_block, dict):
        for key in DESTINATION_BRANCH_KEYS:
            if key in with_block:
                return str(with_block[key])

    # Check 'run' block for CLI flags
    run = step.get("run", "")
    if isinstance(run, str):
        # Look for --base, -B, --destination-branch flags
        flag_patterns = [
            re.compile(r"--base\s+([^\s]+)"),
            re.compile(r"-B\s+([^\s]+)"),
            re.compile(r"--destination-branch\s+([^\s]+)"),
            re.compile(r"--target-branch\s+([^\s]+)"),
            re.compile(r'"base"\s*:\s*"([^"]+)"'),
            re.compile(r"'base'\s*:\s*'([^']+)'"),
            re.compile(r'"base"\s*:\s*\$\{\{([^}]+)\}\}'),
        ]
        for pattern in flag_patterns:
            match = pattern.search(run)
            if match:
                return match.group(1).strip()

    # Check env block
    env_block = step.get("env", {})
    if isinstance(env_block, dict):
        for key in ["BASE_BRANCH", "DESTINATION_BRANCH", "TARGET_BRANCH", "BASE"]:
            if key in env_block:
                return str(env_block[key])

    return None


def uses_dynamic_branch_output(value):
    if value is None:
        return False
    for pattern in DYNAMIC_BRANCH_OUTPUT_PATTERNS:
        if pattern.search(str(value)):
            return True
    return False


def uses_hardcoded_branch(value):
    if value is None:
        return False