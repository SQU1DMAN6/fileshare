#!/usr/bin/env python3

import os
import sys
import requests
import zipfile
import subprocess
from pathlib import Path
import shutil
import importlib

BASE_URL = "https://quanthai.net/repos"
TMP_DIR = "/tmp/fsdl"

def run(cmd):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(1)

def extract_zip(path):
    try:
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(TMP_DIR)
        print(f"Extracted {os.path.basename(path)}")
    except zipfile.BadZipFile:
        print(f"Bad ZIP file: {os.path.basename(path)}")

def clean_tempfolder():
    run("sudo rm -rf /tmp/fsdl")
    print("Cleaning complete")

def detect_and_build(reponame):
    os.chdir(TMP_DIR)
    py_flags = ""

    known_hidden_imports = ['pyttsx3', 'pkg_resources.py2_warn', 'engine', 'comtypes', 'dnspython', 'sympy', 'numpy']
    hidden_imports = [
        f"--hidden-import={mod}"
        for mod in known_hidden_imports
        if importlib.util.find_spec(mod)
    ]
    py_flags += " " + " ".join(hidden_imports)

    if Path("main.py").exists():
        print("Detected Python app. Building with PyInstaller...")

        run("pip install pyinstaller")
        build_cmd = f"sudo pyinstaller --onefile main.py --name {reponame} {py_flags}"
        run(build_cmd)

        binary_path = Path(TMP_DIR) / "dist" / reponame
        if binary_path.exists():
            return str(binary_path)
    elif Path("main.go").exists():
        print("Detected Go app. Building with go build...")
        run(f"go build -o {reponame} main.go")
        return reponame
    elif Path("main.cpp").exists():
        print("Detected C++ app. Building with g++...")
        run(f"g++ main.cpp -o {reponame}")
        return reponame
    elif Path("Makefile").exists():
        print("Makefile found. Running make...")
        run("make")
        return None
    else:
        print("No known entry point found. Please consider checking the repository's source.'")
        return None

def install_binary(binary_path, reponame):
    bin_name = Path(binary_path).name
    dest_bin = f"/usr/local/bin/{bin_name}"
    share_dir = f"/usr/share/{reponame}"

    run(f"chmod +x {binary_path}")
    run(f"sudo cp {binary_path} {dest_bin}")
    run(f"sudo mkdir -p {share_dir}")
    run(f"sudo cp {binary_path} {share_dir}")
    print(f"Installed as '{bin_name}'")

def remove_repo(repo_path):
    if "/" in repo_path:
        _, reponame = repo_path.split("/")
    else:
        reponame = repo_path

    bin_path = f"/usr/local/bin/{reponame}"
    share_path = f"/usr/share/{reponame}"

    if os.path.exists(bin_path):
        run(f"sudo rm -rf {bin_path}")
        print(f"Removed binary from {bin_path}")
    else:
        print("Binary not found in /usr/local/bin")

    if os.path.exists(share_path):
        run(f"sudo rm -rf {share_path}")
        print(f"Removed directory {share_path}")
    else:
        print("Share directory not found")

def get_repo(repo_path, flags):
    no_unzip = "--no-unzip" in flags

    print(f"Fetching repo: {repo_path}")
    full_url = f"{BASE_URL}/{repo_path}"
    os.makedirs(TMP_DIR, exist_ok=True)

    files_to_try = ["main.zip", "app.zip", "root.zip", "install.sh"]
    downloaded = []

    for fname in files_to_try:
        file_url = f"{full_url}/{fname}"
        print(f"Trying {file_url} ...")
        try:
            res = requests.get(file_url)
            if res.status_code == 200:
                local_path = os.path.join(TMP_DIR, fname)
                with open(local_path, "wb") as f:
                    f.write(res.content)
                downloaded.append(fname)
                print(f"Downloaded {fname}")
            else:
                print(f"Not found: {fname}")
        except Exception as e:
            print(f"Error fetching {fname}: {e}")

    if not downloaded:
        print("No files found in repo.")
        sys.exit(1)

    if no_unzip:
        print("--no-unzip used. Skipping extraction and install.")
        return

    for fname in ["main.zip", "app.zip", "root.zip"]:
        path = os.path.join(TMP_DIR, fname)
        if os.path.exists(path):
            extract_zip(path)

    os.chdir(TMP_DIR)
    user, reponame = repo_path.split("/")

    # If install.sh is there, run it — skip FS auto-detection
    if "install.sh" in downloaded:
        print("install.sh found. Running and skipping default installer protocol...")
        os.chmod("install.sh", 0o755)
        result = subprocess.run(["./install.sh"])
        if result.returncode != 0:
            print("install.sh failed. Aborting.")
        return

    # Otherwise, do FS's automatic detection
    print("No install.sh found. Using automatic installer protocol...")
    binary_path = detect_and_build(reponame)
    if binary_path and os.path.exists(binary_path):
        install_binary(binary_path, reponame)
    else:
        print("Build failed or binary not found.")

    print("Done.")

def print_help():
    print("""
FileShare v2, Universal Software Deployer, Written by Quan Thai

Usage:
  fileshare get <user/repo> [--no-unzip]
      Downloads and installs a repo from quanthai.net.
      --no-unzip: Skips extracting and installing — just fetches files into /tmp/fsdl.

  fileshare remove <repo>
      Removes installed binary and associated share directory.

  fileshare clean
      Removes the temporary build directory at /tmp/fsdl.

  fileshare --help
      Shows this help message.
""")

def main():
    if os.geteuid() != 0:
        print("Please run with sudo.")
        sys.exit(1)

    if len(sys.argv) < 2 or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    command = sys.argv[1]
    if command not in ["get", "remove", "clean"]:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)

    if command == "clean":
        clean_tempfolder()
        return

    if len(sys.argv) < 3:
        print("Error: Missing repo path.")
        print_help()
        sys.exit(1)

    repo_path = sys.argv[2].strip("/")
    flags = sys.argv[3:]

    if command == "get":
        get_repo(repo_path, flags)
    elif command == "remove":
        remove_repo(repo_path)

if __name__ == "__main__":
    main()
