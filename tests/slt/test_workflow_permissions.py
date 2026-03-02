import pytest
import yaml
import os
from pathlib import Path


WORKFLOW_FILE = Path(__file__).parent.parent.parent / ".github" / "workflows" / "sdlc-pipeline.yml"


def load_workflow():
    if not WORKFLOW_FILE.exists():
        pytest.fail(f"Workflow file not found at {WORKFLOW_FILE}")
    with open(WORKFLOW_FILE, "r") as f:
        return yaml.safe_load(f)


def get_create_pr_job(workflow):
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if "create-pr" in job_name.lower() or "create_pr" in job_name.lower():
            return job_name, job_config
    return None, None


def get_effective_permissions(workflow, job_config):
    top_level_permissions = workflow.get("permissions", {})
    job_permissions = job_config.get("permissions", {})

    if isinstance(top_level_permissions, str):
        if top_level_permissions == "write-all":
            top_level_permissions = {
                "contents": "write",
                "pull-requests": "write",
            }
        elif top_level_permissions == "read-all":
            top_level_permissions = {
                "contents": "read",
                "pull-requests": "read",
            }
        else:
            top_level_permissions = {}

    if isinstance(job_permissions, str):
        if job_permissions == "write-all":
            job_permissions = {
                "contents": "write",
                "pull-requests": "write",
            }
        elif job_permissions == "read-all":
            job_permissions = {
                "contents": "read",
                "pull-requests": "read",
            }
        else:
            job_permissions = {}

    effective = {}
    effective.update(top_level_permissions)
    effective.update(job_permissions)
    return effective, top_level_permissions, job_permissions


class TestWorkflowFileExists:
    def test_workflow_file_exists(self):
        assert WORKFLOW_FILE.exists(), (
            f"sdlc-pipeline.yml not found at expected path: {WORKFLOW_FILE}"
        )

    def test_workflow_file_is_valid_yaml(self):
        workflow = load_workflow()
        assert workflow is not None, "Workflow file parsed to None — likely empty"
        assert isinstance(workflow, dict), "Workflow file must be a YAML mapping"

    def test_workflow_has_jobs_section(self):
        workflow = load_workflow()
        assert "jobs" in workflow, "Workflow must have a 'jobs' section"
        assert isinstance(workflow["jobs"], dict), "'jobs' must be a mapping"
        assert len(workflow["jobs"]) > 0, "'jobs' section must not be empty"


class TestCreatePrJobExists:
    def test_create_pr_job_present(self):
        workflow = load_workflow()
        job_name, job_config = get_create_pr_job(workflow)
        assert job_name is not None, (
            "No 'create-pr' job found in workflow. "
            f"Available jobs: {list(workflow.get('jobs', {}).keys())}"
        )

    def test_create_pr_job_has_steps(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")
        steps = job_config.get("steps", [])
        assert isinstance(steps, list), "Job 'steps' must be a list"
        assert len(steps) > 0, "create-pr job must have at least one step"


class TestCreatePrJobPermissionsExplicitlyDeclared:
    def test_create_pr_job_has_permissions_block(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions")
        top_level_permissions = workflow.get("permissions")

        assert job_permissions is not None or top_level_permissions is not None, (
            "No permissions declared at job level or workflow level. "
            "Explicit permissions are required for PR creation API calls."
        )

    def test_create_pr_job_explicitly_declares_permissions_at_job_level(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions")
        assert job_permissions is not None, (
            "The create-pr job must explicitly declare a 'permissions' block at the job level. "
            "Relying solely on workflow-level permissions is insufficient for security auditing."
        )

    def test_create_pr_job_permissions_is_not_empty(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions")
        if job_permissions is None:
            pytest.skip("No job-level permissions block — covered by other tests")

        if isinstance(job_permissions, dict):
            assert len(job_permissions) > 0, (
                "The 'permissions' block in create-pr job must not be empty"
            )


class TestContentsWritePermission:
    def test_contents_write_declared_at_job_level(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions", {})
        if isinstance(job_permissions, str):
            if job_permissions == "write-all":
                return
            pytest.fail(
                f"Job permissions is a string shorthand '{job_permissions}' — "
                "explicit 'contents: write' must be declared as a mapping key."
            )

        assert "contents" in job_permissions, (
            "create-pr job must explicitly declare 'contents' permission. "
            f"Current job-level permissions: {job_permissions}"
        )

    def test_contents_permission_is_write(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions", {})
        if isinstance(job_permissions, str):
            if job_permissions == "write-all":
                return
            pytest.skip("Permissions declared as string shorthand")

        contents_value = job_permissions.get("contents")
        if contents_value is None:
            pytest.fail(
                "create-pr job does not declare 'contents' permission at job level. "
                "PR creation requires 'contents: write'."
            )

        assert contents_value == "write", (
            f"create-pr job 'contents' permission must be 'write', got '{contents_value}'. "
            "PR creation API calls require write access to repository contents."
        )

    def test_contents_write_not_read_only(self):
        workflow = load_workflow()
        _, job_config = get_create_pr_job(workflow)
        if job_config is None:
            pytest.skip("create-pr job not found")

        job_permissions = job_config.get("permissions", {})
        if isinstance(job_permissions, str):
            pytest.skip("Permissions declared as string shorthand")

        contents_value = job_permissions.get("contents", "")
        assert contents_value != "read", (
            "create-pr job has 'contents: read' but 'contents: write' is required. "