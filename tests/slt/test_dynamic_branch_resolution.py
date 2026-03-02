import pytest
import subprocess
import json
import os
import tempfile
from unittest.mock import patch, MagicMock, call
import sys

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

REPOSITORY = "my-org/my-repo"
DEFAULT_BRANCH = "main"

GH_API_SUCCESS_RESPONSE = json.dumps({
    "id": 123456789,
    "name": "my-repo",
    "full_name": REPOSITORY,
    "default_branch": DEFAULT_BRANCH,
    "private": False,
    "description": "Test repository",
})

GH_API_RENAMED_BRANCH_RESPONSE = json.dumps({
    "id": 123456789,
    "name": "my-repo",
    "full_name": REPOSITORY,
    "default_branch": "trunk",
    "private": False,
    "description": "Test repository with renamed default branch",
})

GH_API_MASTER_BRANCH_RESPONSE = json.dumps({
    "id": 123456789,
    "name": "my-repo",
    "full_name": REPOSITORY,
    "default_branch": "master",
    "private": False,
    "description": "Test repository with master branch",
})

GH_API_MISSING_FIELD_RESPONSE = json.dumps({
    "id": 123456789,
    "name": "my-repo",
    "full_name": REPOSITORY,
    "private": False,
})

GH_API_EMPTY_RESPONSE = json.dumps({})

GH_API_MALFORMED_RESPONSE = "this is not valid json {"

GH_API_ERROR_RESPONSE = json.dumps({
    "message": "Not Found",
    "documentation_url": "https://docs.github.com/rest/repos/repos#get-a-repository",
})


# ---------------------------------------------------------------------------
# Unit-level: pure Python logic that mirrors the shell/action script
# ---------------------------------------------------------------------------

def resolve_default_branch(repository: str) -> str:
    """
    Mirrors the dynamic branch resolution logic expected in the pipeline.
    Calls `gh api repos/{repository}` and extracts `default_branch`.
    Raises RuntimeError on failure.
    """
    cmd = ["gh", "api", f"repos/{repository}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise RuntimeError(
            f"gh api call failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse gh api response as JSON: {exc}") from exc

    if "default_branch" not in data:
        raise RuntimeError(
            f"'default_branch' field missing from gh api response. "
            f"Keys present: {list(data.keys())}"
        )

    branch = data["default_branch"]
    if not branch or not isinstance(branch, str):
        raise RuntimeError(
            f"'default_branch' value is invalid: {branch!r}"
        )

    return branch


def write_branch_to_github_output(branch: str, output_file: str) -> None:
    """
    Writes `branch=<value>` to the GITHUB_OUTPUT file.
    """
    with open(output_file, "a", encoding="utf-8") as fh:
        fh.write(f"branch={branch}\n")


def dynamic_branch_resolution_step(repository: str, github_output_path: str) -> str:
    """
    Full step: resolve branch via API, write to GITHUB_OUTPUT, return branch.
    """
    branch = resolve_default_branch(repository)
    write_branch_to_github_output(branch, github_output_path)
    return branch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def github_output_file():
    """Provides a temporary file simulating GITHUB_OUTPUT."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
        tmp_path = tmp.name
    yield tmp_path
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def mock_subprocess_success():
    """Mocks subprocess.run to return a successful gh api response."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_SUCCESS_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_trunk():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_RENAMED_BRANCH_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_master():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_MASTER_BRANCH_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_api_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = GH_API_ERROR_RESPONSE
    mock_result.stderr = "gh: Not Found (HTTP 404)"
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_malformed_json():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_MALFORMED_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_missing_field():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_MISSING_FIELD_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_empty_response():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = GH_API_EMPTY_RESPONSE
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        yield mock_run


# ---------------------------------------------------------------------------
# Test Class: API call construction
# ---------------------------------------------------------------------------

class TestGhApiCallConstruction:
    """Verify that the correct gh api command is constructed and invoked."""

    def test_calls_gh_api_with_correct_endpoint(self, mock_subprocess_success):
        resolve_default_branch(REPOSITORY)
        mock_subprocess_success.assert_called_once()
        args, kwargs = mock_subprocess_success.call_args
        cmd = args[0]
        assert cmd[0] == "gh", "First argument must be 'gh'"
        assert cmd[1] == "api", "Second argument must be 'api'"
        assert cmd[2] == f"repos/{REPOSITORY}", (
            f"Third argument must be 'repos/{REPOSITORY}'"
        )

    def test_command_is_list_not_string(self, mock_subprocess_success):
        resolve_default_branch(REPOSITORY)
        args, _ = mock_subprocess_success.call_args
        cmd = args[0]
        assert