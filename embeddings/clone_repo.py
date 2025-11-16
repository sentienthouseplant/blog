# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "gitpython",
#     "click",
# ]
# ///


import contextlib
import tempfile
import os

import git
import click


@contextlib.contextmanager
def clone_repo(repo_owner: str, repo_name: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_auth_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        repo = git.Repo.clone_from(repo_auth_url, temp_dir)
        yield repo


@click.group()
def cli():
    pass

@cli.command()
@click.option("--repo-owner", required=True)
@click.option("--repo-name", required=True)
def tree(repo_owner: str, repo_name: str):
    with clone_repo(repo_owner, repo_name) as repo:
        for item in os.listdir(repo.working_tree_dir):
            print(item)

if __name__ == "__main__":
    cli()