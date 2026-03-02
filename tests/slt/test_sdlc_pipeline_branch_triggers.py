import pytest
import yaml
import os
import re
from pathlib import Path


WORKFLOW_FILE_PATHS = [
    ".github/workflows/sdlc-pipeline.yml",
    "../.github/workflows/sdlc-pipeline.yml",
    "../../.github/workflows/sdlc-pipeline.yml",
]


def find_workflow_file():
    """Locate the sdlc-pipeline.yml workflow file by searching common relative paths."""
    # Start from the test file's directory and walk up
    test_dir = Path(__file__).parent
    
    # Try direct relative paths from test file location
    search_roots = [
        test_dir,
        test_dir.parent,
        test_dir.parent.parent,
        test_dir.parent.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    
    for root in search_roots:
        candidate = root / ".github" / "workflows" / "sdlc-pipeline.yml"
        if candidate.exists():
            return candidate
    
    # Also try environment variable override
    env_path = os.environ.get("WORKFLOW_FILE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    
    return None


@pytest.fixture(scope="module")
def workflow_file_path():
    """Fixture that returns the path to the workflow file."""
    path = find_workflow_file()
    if path is None:
        pytest.fail(
            "Could not locate .github/workflows/sdlc-pipeline.yml. "
            "Ensure the test is run from within the repository or set "
            "WORKFLOW_FILE_PATH environment variable."
        )
    return path


@pytest.fixture(scope="module")
def workflow_raw_content(workflow_file_path):
    """Fixture that returns the raw string content of the workflow file."""
    return workflow_file_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_parsed(workflow_raw_content):
    """Fixture that returns the parsed YAML content of the workflow file."""
    try:
        parsed = yaml.safe_load(workflow_raw_content)
    except yaml.YAMLError as exc:
        pytest.fail(f"Failed to parse sdlc-pipeline.yml as valid YAML: {exc}")
    return parsed


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def extract_on_section(parsed):
    """Return the 'on' trigger section from the parsed workflow."""
    # PyYAML maps the YAML key 'on' to Python boolean True in some versions,
    # but in others it keeps it as the string 'on'. Handle both.
    on_section = parsed.get("on") or parsed.get(True)
    return on_section


def collect_branches_for_event(on_section, event_name):
    """
    Given the 'on' section and an event name ('push' or 'pull_request'),
    return the list of branch patterns configured for that event.
    Returns an empty list if the event is not configured or has no branch filters.
    """
    if on_section is None:
        return []
    
    event_config = on_section.get(event_name)
    if event_config is None:
        return []
    
    # The event config can be None (bare trigger), a dict, or a list
    if isinstance(event_config, dict):
        branches = event_config.get("branches") or []
        return branches if isinstance(branches, list) else [branches]
    
    return []


def branches_contain_pattern(branches, pattern):
    """Return True if the given pattern is present in the branches list."""
    return pattern in branches


def branches_contain_master(branches):
    """Return True if any branch pattern references 'master'."""
    for b in branches:
        if b is None:
            continue
        if "master" in str(b):
            return True
    return False


# ---------------------------------------------------------------------------
# File existence and parse tests
# ---------------------------------------------------------------------------

class TestWorkflowFileExists:
    """Verify the workflow file can be found and is valid YAML."""

    def test_workflow_file_exists(self, workflow_file_path):
        """The sdlc-pipeline.yml file must exist on disk."""
        assert workflow_file_path.exists(), (
            f"Workflow file not found at {workflow_file_path}"
        )

    def test_workflow_file_is_not_empty(self, workflow_raw_content):
        """The workflow file must not be empty."""
        assert workflow_raw_content.strip(), "sdlc-pipeline.yml is empty."

    def test_workflow_file_parses_as_valid_yaml(self, workflow_parsed):
        """The workflow file must be parseable as valid YAML."""
        assert workflow_parsed is not None, "Parsed YAML is None — file may be empty."
        assert isinstance(workflow_parsed, dict), (
            "Top-level YAML structure must be a mapping (dict)."
        )

    def test_workflow_has_on_section(self, workflow_parsed):
        """The workflow must have an 'on' trigger section."""
        on_section = extract_on_section(workflow_parsed)
        assert on_section is not None, (
            "Workflow is missing the 'on' trigger section."
        )


# ---------------------------------------------------------------------------
# Push trigger tests
# ---------------------------------------------------------------------------

class TestPushTrigger:
    """Verify push trigger configuration targets 'main' and not 'master'."""

    def test_push_trigger_is_defined(self, workflow_parsed):
        """The workflow must define a 'push' trigger."""
        on_section = extract_on_section(workflow_parsed)
        assert on_section is not None, "Missing 'on' section."
        assert "push" in on_section, (
            "The workflow does not define a 'push' trigger."
        )

    def test_push_trigger_has_branch_filter(self, workflow_parsed):
        """The push trigger must specify branch filters."""
        on_section = extract_on_section(workflow_parsed)
        branches = collect_branches_for_event(on_section, "push")
        assert len(branches) > 0, (
            "The 'push' trigger does not specify any branch filters. "
            "Expected at least 'main'."
        )

    def test_push_trigger_includes_main_branch(self, workflow_parsed):
        """The push trigger must include 'main' as a target branch."""
        on_section = extract_on_section(workflow_parsed)
        branches = collect_branches_for_event(on_section, "push")
        assert branches_contain_pattern(branches, "main"), (
            f"The 'push' trigger branch list {branches} does not include 'main'. "
            "Expected 'main' to be listed as a target branch."
        )

    def test_push_trigger_does_not_include_master_branch(self, workflow_parsed):
        """The push trigger must NOT include 'master' as a target branch."""
        on_section = extract_on_section(workflow_parsed)
        branches = collect_branches_for_event(on_section, "push")
        assert not branches_contain_master(branches), (
            f"The 'push' trigger branch list {branches} contains a reference to "
            "'master'. All references to 'master' must be replaced with 'main'."
        )

    def test_push_trigger_main_is_exact_match_not_substring(self, workflow_parsed):
        """Ensure 'main' appears as an exact branch name, not just a substring."""
        on_section = extract_on_section(workflow_parsed)
        branches = collect_branches_for_event(on_section, "push")
        # 'main' should be present as a standalone entry
        assert "main" in branches, (
            f"'main' must appear as an exact branch entry in push branches: {branches}"
        )


# ---------------------------------------------------------------------------
# Pull request trigger tests
# ---------------------------------------------------------------------------

class TestPullRequestTrigger:
    """Verify pull_request trigger configuration targets 'main' and not '