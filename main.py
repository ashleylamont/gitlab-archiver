import os
import subprocess
from datetime import datetime
from enum import Enum

import gitlab
import prompt_toolkit.shortcuts
from dotenv import load_dotenv
import questionary
from gitlab.v4.objects import Project
from dateutil import parser
from git import Repo
from tempfile import TemporaryDirectory

load_dotenv()


class ArchiveMode(Enum):
    SINGLE_REPO = 1
    DOWNLOAD_AND_DELETE = 2
    DELETE = 3

    def __str__(self):
        if self == ArchiveMode.SINGLE_REPO:
            return "Archive into single repo"
        elif self == ArchiveMode.DOWNLOAD_AND_DELETE:
            return "Download archives and delete"
        elif self == ArchiveMode.DELETE:
            return "Delete without saving"

    @staticmethod
    def from_str(mode: str) -> "ArchiveMode":
        for enum in ArchiveMode:
            if str(enum) == mode:
                return enum
        raise ValueError(f"Invalid mode: {mode}")


def main():
    gl = gitlab.Gitlab(url=os.environ.get("GITLAB_SERVER"),
                       private_token=os.environ.get("GITLAB_TOKEN"))
    gl.auth()
    user = gl.user
    project_limit = user.projects_limit
    projects: list[Project] = gl.projects.list(get_all=True, owned=True,
                                               order_by="last_activity_at")
    project_descriptors = {
        f"{project.name_with_namespace} (Last activity {parser.parse(project.last_activity_at).strftime("%m/%d/%Y, %H:%M")})": project
        for project in projects}
    project_count = len(projects)
    remaining_projects = project_limit - project_count
    if remaining_projects <= 0:
        questionary.print(
            f"You have reached the project limit of {project_limit} projects. "
            f"You will need to delete one or more projects manually to use "
            f"the 'Archive into single repo' mode.",
            style="bold fg:red")
    elif remaining_projects <= 5:
        questionary.print(
            f"You have {remaining_projects} projects left before reaching the "
            f"project limit of {project_limit}.",
            style="bold fg:yellow")
    else:
        questionary.print(
            f"You have {remaining_projects} projects left before reaching the "
            f"project limit of {project_limit}.",
            style="bold fg:green")
    questionary.press_any_key_to_continue().ask()
    projects_to_archive = questionary.checkbox(
        "Select projects to archive", choices=project_descriptors).ask()
    archival_mode = questionary.select(
        "Select archival mode",
        choices=[str(mode) for mode in ArchiveMode]).ask()
    archival_mode_enum = ArchiveMode.from_str(archival_mode)
    if archival_mode_enum == ArchiveMode.SINGLE_REPO:
        ssh_or_https = questionary.select(
            "Select protocol for cloning",
            choices=["SSH", "HTTPS"], default="SSH").ask()
        if ssh_or_https == "SSH":
            # Verify that the user has set up SSH keys
            ssh_proc = subprocess.run(
                ["ssh", "-T", "git@gitlab.cecs.anu.edu.au"],
                capture_output=True)
            if ssh_proc.returncode != 0:
                questionary.print("You need to set up SSH keys before using "
                                  "this mode.",
                                  style="bold fg:red")
                return
            else:
                questionary.print("SSH keys are set up already!",
                                  style="bold fg:green")
        else:
            # Verify that the user has set up HTTPS credentials
            # idk how to do this so get rekt if you use HTTPS
            questionary.print(
                "You may get prompted for your GitLab username and password.",
                style="bold fg:yellow")
        tmp_dir = TemporaryDirectory("_gitlab-archive")
        questionary.print(f"Created temporary directory {tmp_dir.name}",
                          style="italic fg:green")
        main_repo = Repo.init(tmp_dir.name)
        questionary.print(f"Initialized main repository in {tmp_dir.name}",
                          style="italic fg:green")
        upstream_project_id = f"project-archive-{datetime.now().strftime(
            '%Y-%m-%d-%H-%M-%S')}"
        upstream_project = gl.projects.create({'name': upstream_project_id})
        questionary.print(f"Created upstream project {upstream_project_id}",
                          style="italic fg:green")
        main_repo.create_remote("origin", upstream_project.ssh_url_to_repo
        if ssh_or_https == "SSH"
        else upstream_project.http_url_to_repo)
        for project_descriptor in projects_to_archive:
            project = project_descriptors[project_descriptor]
            project_id = str(project.id)
            project_remote = main_repo.create_remote(project_id,
                                                     project.ssh_url_to_repo
                                                     if ssh_or_https == "SSH"
                                                     else project.http_url_to_repo)
            project_remote.fetch()
            questionary.print(f"Grabbing branches from {project_descriptor}",
                              style="italic fg:green")
            project_branches = project.branches.list()
            for remote_branch in project_branches:
                questionary.print(
                    f"Checking out branch {remote_branch.name} from {project_descriptor}",
                    style="italic fg:green")
                main_branch_name = f"{project.path_with_namespace}/{remote_branch.name}"
                main_repo.git.checkout("-b", main_branch_name,
                                       f"{project_id}/{remote_branch.name}")
                questionary.print(
                    f"Checked out branch {remote_branch.name} from {project_descriptor}",
                    style="italic fg:green")
        questionary.print("Pushing branches to upstream project",
                          style="italic fg:green")
        main_repo.git.push("--all", "origin")
        questionary.print("Pushed branches to upstream project",
                          style="italic fg:green")
        delete_projects = questionary.confirm(
            f"Your new project is available at {upstream_project.web_url}.\n" +
            f"Do you want to delete the original projects?\n" +
            f"This action cannot be undone.").ask()
        if delete_projects:
            for project_descriptor in projects_to_archive:
                project = project_descriptors[project_descriptor]
                project.delete()
                questionary.print(f"Deleted project {project_descriptor}",
                                  style="bold fg:yellow")
    elif archival_mode_enum == ArchiveMode.DOWNLOAD_AND_DELETE:
        file_path = questionary.path("Select directory to save archives",
                                     only_directories=True,
                                     complete_style=prompt_toolkit.shortcuts.CompleteStyle.MULTI_COLUMN,
                                     ).ask()
        if not file_path:
            questionary.print("No directory selected. Exiting.",
                              style="bold fg:red")
            return
        for project_descriptor in projects_to_archive:
            project = project_descriptors[project_descriptor]
            for branch in project.branches.list():
                branch_name = branch.name
                branch_archive = project.repository_archive(
                    ref=branch_name, format="tar.gz")
                file_path = os.path.expanduser(file_path)
                file_path = os.path.expandvars(file_path)
                with open(
                    f"{file_path}/{project.path_with_namespace.replace('/', '-')}-"
                    f"{branch_name.replace('/', '-')}.tar.gz",
                    "wb+") as archive_file:
                    archive_file.write(branch_archive)
                questionary.print(
                    f"Downloaded archive for branch {branch_name} from "
                    f"{project_descriptor}",
                    style="italic fg:green")
        delete_projects = questionary.confirm(
            f"Archives have been saved to {file_path}.\n" +
            f"Do you want to delete the original projects?\n" +
            f"This action cannot be undone.").ask()
        if delete_projects:
            for project_descriptor in projects_to_archive:
                project = project_descriptors[project_descriptor]
                project.delete()
                questionary.print(f"Deleted project {project_descriptor}",
                                  style="bold fg:yellow")
    elif archival_mode_enum == ArchiveMode.DELETE:
        delete_projects = questionary.confirm(
            f"Do you want to delete the original projects?\n" +
            f"This action cannot be undone.").ask()
        if delete_projects:
            for project_descriptor in projects_to_archive:
                project = project_descriptors[project_descriptor]
                project.delete()
                questionary.print(f"Deleted project {project_descriptor}",
                                  style="bold fg:yellow")


if __name__ == '__main__':
    main()
