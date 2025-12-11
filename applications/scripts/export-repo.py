#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: Apache-2.0
# Copyright Pionix GmbH and Contributors to EVerest
#
"""
author: andreas.heinrich@rwth-aachen.de
This script exports changes from a specified subdirectory of an origin git repository
to a target git repository. It creates a patch from the latest commit in the origin
repository that affects the specified subdirectory, applies this patch to the target
repository, and replaces a specified placeholder in a given file within the target
repository with a reference to the latest commit (either tag or hash) from the origin
repository. Finally, it creates a new commit in the target repository with a message
that includes the original commit message from the origin repository.
"""


import argparse
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def checkout_target_repo(args: argparse.Namespace):
    try:
        res = subprocess.run(
            [
                "git",
                "clone",
                "--branch", args.target_repo_branch,
                args.target_repo_url,
                args.target_repo_root_dir.as_posix(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone target repository from '{args.target_repo_url}': {e.stderr.strip()}") from e
    print(res.stdout)


def check_changes_in_subdirectory(args: argparse.Namespace) -> bool:
    changed_files = []
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.origin_repo_root_dir.as_posix(),
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get changed files from origin repository: {e.stderr.strip()}") from e
    changed_files = res.stdout.strip().split('\n')

    for file in changed_files:
        file_path = Path(file)
        if not file_path.is_relative_to(args.source_subdirectory.relative_to(args.origin_repo_root_dir)):
            continue
        else:
            return True
    return False


def create_patch(args: argparse.Namespace) -> str:
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.origin_repo_root_dir.as_posix(),
                "format-patch",
                "-1",
                "HEAD",
                f"--relative={args.source_subdirectory.relative_to(args.origin_repo_root_dir).as_posix()}",
                "--stdout",
                "--",
                args.source_subdirectory.relative_to(args.origin_repo_root_dir).as_posix(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create patch from origin repository: {e.stderr.strip()}") from e
    return res.stdout


def apply_patch_to_target_repo(args: argparse.Namespace, patch: str):
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.target_repo_root_dir.as_posix(),
                "apply",
                "--index",
            ],
            input=patch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply patch to target repository: {e.stderr.strip()}") from e
    print(res.stdout)


def get_latest_commit_ref(args: argparse.Namespace) -> str:
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.origin_repo_root_dir.as_posix(),
                "rev-parse",
                "HEAD",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get latest commit hash from repository '{args.origin_repo_root_dir}': {e.stderr.strip()}") from e
    commit_hash = res.stdout.strip()

    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.origin_repo_root_dir.as_posix(),
                "describe",
                "--tags",
                "--exact-match",
                commit_hash,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        tag = res.stdout.strip()
        return tag
    except subprocess.CalledProcessError:
        return commit_hash


def replace_placeholer(args: argparse.Namespace, ref_latest_commit: str):
    try:
        with open(args.replace_placeholder_file, "r") as f:
            content = f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read file '{args.replace_placeholder_file}': {e}") from e

    new_content = content.replace(args.replace_placeholder, ref_latest_commit)

    try:
        with open(args.replace_placeholder_file, "w") as f:
            f.write(new_content)
    except Exception as e:
        raise RuntimeError(f"Failed to write file '{args.replace_placeholder_file}': {e}") from e
    
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.target_repo_root_dir.as_posix(),
                "add",
                args.replace_placeholder_file.relative_to(args.target_repo_root_dir).as_posix(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to stage modified file '{args.replace_placeholder_file}' in target repository: {e.stderr.strip()}") from e
    print(res.stdout)

def get_latest_commit_message(args: argparse.Namespace) -> str:
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.origin_repo_root_dir.as_posix(),
                "log",
                "-1",
                "--pretty=%B",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get latest commit message from origin repository: {e.stderr.strip()}") from e
    return res.stdout.strip()

def create_commit(args: argparse.Namespace, original_commit_message: str, ref_latest_commit: str):
    commit_message = f"Import changes from origin repository @ {ref_latest_commit}\n\n"
    commit_message += f"Replaced placeholder '{args.replace_placeholder}' in file '{args.replace_placeholder_file.as_posix()}' with reference to latest commit.\n\n"
    commit_message += "Original commit message:\n\n"
    for line in original_commit_message.splitlines():
        commit_message += f"> {line}\n"
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.target_repo_root_dir.as_posix(),
                "commit",
                "-s",
                "-m",
                commit_message,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create commit in target repository: {e.stderr.strip()}") from e
    print(res.stdout)


def deploy_target_repo(args: argparse.Namespace):
    try:
        res = subprocess.run(
            [
                "git",
                "-C", args.target_repo_root_dir.as_posix(),
                "push",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to push changes to remote in target repository: {e.stderr.strip()}") from e
    print(res.stdout)


def main():
    parser = argparse.ArgumentParser(description="Export changes from a subdirectory of an origin git repository to a target git repository, replacing a placeholder in a specified file with the latest commit reference.")
    parser.add_argument("--origin-repo-root-dir", type=str, help="Origin repository root directory", required=True)
    parser.add_argument("--source-subdirectory", type=str, help="Source subdirectory to export", required=True)
    parser.add_argument("--target-repo-url", type=str, help="Target repository URL", required=True)
    parser.add_argument("--target-repo-branch", type=str, help="Target repository branch to checkout", default="main", required=False)
    parser.add_argument("--target-repo-root-dir", type=str, help="Target repository root directory", required=True)
    parser.add_argument("--replace-placeholder", type=str, help="Placeholder string to replace in the target file", required=True)
    parser.add_argument("--replace-placeholder-file", type=str, help="File in which to replace the placeholder", required=True)
    parser.add_argument("--do-not-deploy", type=bool, help="If set, do not perform deployment steps (for testing purposes)", default=False, required=False)
    args = parser.parse_args()

    # Validate parameter origin_repo_root_dir
    args.origin_repo_root_dir = Path(args.origin_repo_root_dir).expanduser().resolve()
    if not args.origin_repo_root_dir.is_dir():
        raise FileNotFoundError(f"Origin repository directory '{args.origin_repo_root_dir}' does not exist.")
    # check if it's a git repository
    res = subprocess.run(
        [
            "git",
            "-C", str(args.origin_repo_root_dir),
            "rev-parse",
            "--is-inside-work-tree",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    if res.returncode != 0:
        raise ValueError(f"Origin repository directory '{args.origin_repo_root_dir}' is not a git repository.")


    # Validate parameter source_subdirectory
    args.source_subdirectory = Path(args.source_subdirectory)
    if not args.source_subdirectory.is_absolute():
        args.source_subdirectory = args.origin_repo_root_dir / args.source_subdirectory
    args.source_subdirectory = args.source_subdirectory.expanduser().resolve()
    if not args.source_subdirectory.is_relative_to(args.origin_repo_root_dir):
        raise ValueError(f"Source subdirectory '{args.source_subdirectory}' is not relative to origin repository '{args.origin_repo_root_dir}'.")

    # Validate parameter target_repo_root_dir
    args.target_repo_root_dir = Path(args.target_repo_root_dir).expanduser()
    if not args.target_repo_root_dir.is_absolute():
        raise ValueError(f"Target repository root directory '{args.target_repo_root_dir}' must be an absolute path.")
    if args.target_repo_root_dir.exists():
        raise FileExistsError(f"Target repository root directory '{args.target_repo_root_dir}' already exists.")
    
    # Validate parameter replace_placeholder
    if len(args.replace_placeholder.strip()) < 3:
        raise ValueError("Replace placeholder must be at least 3 characters long.")
    
    # Validate parameter replace_placeholder_file
    args.replace_placeholder_file = Path(args.replace_placeholder_file)
    if args.replace_placeholder_file.is_absolute():
        raise ValueError("Replace placeholder file must be a relative path. It must be relative to the subdirectory in the origin repository.")
    args.replace_placeholder_file = args.target_repo_root_dir / args.replace_placeholder_file

    checkout_target_repo(args)
    if not check_changes_in_subdirectory(args):
        print(f"No changes in source subdirectory '{args.source_subdirectory}' detected in origin repository. Exiting.")
        exit(0)
    patch = create_patch(args)
    apply_patch_to_target_repo(args, patch)
    
    args.replace_placeholder_file.expanduser().resolve()
    if not args.replace_placeholder_file.is_file():
        raise FileNotFoundError(f"Replace placeholder file '{args.replace_placeholder_file}' does not exist.")

    ref_latest_commit = get_latest_commit_ref(args)
    replace_placeholer(args, ref_latest_commit)

    original_commit_message = get_latest_commit_message(args)
    create_commit(args, original_commit_message, ref_latest_commit)
    
    if not args.do_not_deploy:
        deploy_target_repo(args)
    else:
        print("Skipping deployment steps as per --do-not-deploy flag.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
