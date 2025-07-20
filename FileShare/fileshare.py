#!/usr/bin/env python3

import os
import sys
import requests
import zipfile
import subprocess
from pathlib import Path

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

def detect_and_build():
    os.chdir(TMP_DIR)
    if Path("main.py").exists():
        print("Detected Python app. Building with PyInstaller...")
        run("pip install pyinstaller")
        run("pyinstaller --onefile main.py")
        return "dist/main"
    elif Path("main.go").exists():
        print("Detected Go app. Building with go build...")
        run("go build -o app_bin main.go")
        return "app_bin"
    elif Path("main.cpp").exists():
        print("Detected C++ app. Building with g++...")
        run("g++ main.cpp -o app_bin")
        return "app_bin"
    elif Path("Makefile").exists():
        print("Makefile found. Running make...")
        run("make")
        return None
    else:
        print("No known entry point found. Please consider using --no-unzip or --ignore-default.")
        return None

def install_binary(binary_path, reponame):
    bin_name = Path(binary_path).name
    run(f"chmod +x {binary_path}")
    run(f"sudo cp {binary_path} /usr/local/bin/{bin_name}")
    run(f"sudo mkdir -p /usr/share/{reponame}/")
    run(f"sudo cp {binary_path} /usr/share/{reponame}/")
    print(f"Installed as '{bin_name}'")
    run("sudo rm -rf /tmp/fsdl")

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
    ignore_default = "--ignore-default" in flags

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

    if not no_unzip:
        for fname in ["main.zip", "app.zip", "root.zip"]:
            path = os.path.join(TMP_DIR, fname)
            if os.path.exists(path):
                extract_zip(path)

    install_script = os.path.join(TMP_DIR, "install.sh")
    user, reponame = repo_path.split("/")

    if ignore_default and "install.sh" in downloaded:
        print("Running install.sh ...")
        os.chmod(install_script, 0o755)
        subprocess.run([install_script], cwd=TMP_DIR)
    else:
        print("Using automatic language detection...")
        binary_path = detect_and_build()
        if binary_path and os.path.exists(binary_path):
            install_binary(binary_path, reponame)
        else:
            print("Build failed or output binary not found.")

    print("Done.")

def print_help():
    print("""
fileshare - lightweight universal repo fetcher & builder

Usage:
  fileshare get <user/repo> [--no-unzip] [--ignore-default]
      Downloads and installs a repo from quanthai.net.
      --no-unzip: Skips extracting downloaded zip files.
      --ignore-default: Runs install.sh if available instead of auto-detect.

  fileshare remove <user/repo>
      Removes installed binary and associated share directory.

  fileshare clean
      Wipes the temporary build directory at /tmp/fsdl.

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
