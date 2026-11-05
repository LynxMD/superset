# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Guard tests: `.python-version` is the single source of the Python version.

Every Docker image and build script must take the version from that file.
Example: to move to Python 3.15, a developer edits `.python-version` only, and
the Dockerfiles, the GitHub workflows, the CI image build, the release scripts and the Makefile all
follow.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_VERSION = (REPO_ROOT / ".python-version").read_text().strip()
HARDCODED_PYTHON = re.compile(r"python:?3\.\d+")


def tracked_files(*patterns: str) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--", *patterns],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [REPO_ROOT / line for line in out.splitlines()]


def python_dockerfiles() -> list[Path]:
    files = tracked_files("Dockerfile", "*/Dockerfile", "*Dockerfile.*", "*.Dockerfile")
    return [f for f in files if re.search(r"^FROM python", f.read_text(), re.M)]


def docker_build_commands(path: Path) -> list[str]:
    """Return every `docker build` command in a shell script or workflow."""
    text = path.read_text().replace("\\\n", " ")
    return [
        line
        for line in text.splitlines()
        if re.search(r"\bdocker (buildx )?build\b", line)
        and not line.lstrip().startswith(("#", "echo"))
    ]


def test_python_version_file_holds_a_plain_version() -> None:
    assert re.fullmatch(r"3\.\d+", PYTHON_VERSION), PYTHON_VERSION


def test_python_version_file_is_not_git_ignored() -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", ".python-version"],
        cwd=REPO_ROOT,
    )
    assert ignored.returncode == 1


def test_there_are_python_dockerfiles_to_check() -> None:
    names = {str(f.relative_to(REPO_ROOT)) for f in python_dockerfiles()}
    assert "Dockerfile" in names
    assert "RELEASING/Dockerfile.make_tarball" in names


@pytest.mark.parametrize(
    "dockerfile", python_dockerfiles(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_dockerfile_takes_python_version_from_build_arg(dockerfile: Path) -> None:
    text = dockerfile.read_text()
    assert not HARDCODED_PYTHON.search(text), "hardcoded Python version"
    assert re.search(r"^ARG PY_VER\s*$", text, re.M), "needs `ARG PY_VER`"
    assert not re.search(r"^ARG PY_VER=", text, re.M), "PY_VER needs no default"
    for line in re.findall(r"^FROM python.*$", text, re.M):
        assert line.startswith("FROM python:${PY_VER}"), line


@pytest.mark.parametrize(
    "script",
    [
        ".github/workflows/docker_build_push.sh",
        ".github/workflows/docker.yml",
        "RELEASING/make_tarball.sh",
        "RELEASING/test_run_tarball.sh",
    ],
)
def test_build_script_passes_python_version(script: str) -> None:
    commands = docker_build_commands(REPO_ROOT / script)
    assert commands
    for command in commands:
        assert "--build-arg PY_VER=" in command and ".python-version" in command


@pytest.mark.parametrize(
    "compose", ["docker-compose.yml", "docker-compose-non-dev.yml"]
)
def test_compose_has_no_hardcoded_python_version(compose: str) -> None:
    text = (REPO_ROOT / compose).read_text()
    assert not re.search(r"(python|superset-cache):3\.\d+", text)


def test_makefile_reads_python_version_file() -> None:
    text = (REPO_ROOT / "Makefile").read_text()
    assert not HARDCODED_PYTHON.search(text), "hardcoded Python version"
    assert "cat .python-version" in text


HARDCODED_CI_PYTHON = re.compile(r"(?i)python[\w-]*[\"']?\s*[:=]\s*\[?\s*[\"']?3\.\d+")
SETUP_PYTHON_STEPS = ("actions/setup-python", "./.github/actions/setup-backend")


def ci_files() -> list[Path]:
    return tracked_files(".github/*.yml", ".github/*.yaml", ".github/*.sh")


def workflow_jobs() -> list[tuple[str, str, list[dict[str, Any]]]]:
    jobs = []
    for path in tracked_files(".github/workflows/*.yml"):
        for name, job in (yaml.safe_load(path.read_text()).get("jobs") or {}).items():
            jobs.append((path.name, name, job.get("steps") or []))
    return jobs


def all_steps() -> list[tuple[str, dict[str, Any]]]:
    steps = [
        (f"{wf}:{job}", step)
        for wf, job, job_steps in workflow_jobs()
        for step in job_steps
    ]
    for path in tracked_files(".github/actions/*.yml"):
        action = yaml.safe_load(path.read_text())
        for step in action.get("runs", {}).get("steps") or []:
            steps.append((str(path.relative_to(REPO_ROOT)), step))
    return steps


@pytest.mark.parametrize(
    "path", ci_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_ci_has_no_hardcoded_python_version(path: Path) -> None:
    for number, line in enumerate(path.read_text().splitlines(), 1):
        assert not HARDCODED_CI_PYTHON.search(line), f"line {number}: {line.strip()}"


def test_setup_python_reads_python_version_file() -> None:
    setups = [
        (where, step)
        for where, step in all_steps()
        if str(step.get("uses", "")).startswith("actions/setup-python")
    ]
    assert setups
    for where, step in setups:
        options = step.get("with") or {}
        assert options.get("python-version-file") == ".python-version", where
        assert "python-version" not in options, where


def test_checkout_comes_before_python_setup() -> None:
    """`python-version-file` needs the repo on disk before Python is set up."""
    for workflow, job, steps in workflow_jobs():
        for index, step in enumerate(steps):
            if str(step.get("uses", "")).startswith(SETUP_PYTHON_STEPS):
                before = [str(s.get("uses", "")) for s in steps[:index]]
                assert any(
                    u.startswith("actions/checkout") for u in before
                ), f"{workflow}:{job}"
