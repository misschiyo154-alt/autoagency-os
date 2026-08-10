import sys
from pathlib import Path
import subprocess

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from config import COMMIT_MESSAGE, GITHUB_BRANCH


def run_command(command, label):
    print(f"\n🔄 {label}...")

    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True
        )

        if result.stdout.strip():
            print(result.stdout.strip())

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ {label} failed.")

        if e.stdout:
            print(e.stdout.strip())

        if e.stderr:
            print(e.stderr.strip())

        return False


def main():

    print("\n🚀 Updating GitHub...")

    # ==========================
    # GIT STATUS
    # ==========================

    status = subprocess.run(
        ["git", "status", "--short"],
        text=True,
        capture_output=True
    )

    if status.stdout.strip():
        print("\n📋 Changes:")
        print(status.stdout.strip())
    else:
        print("\nℹ️ No changes to commit.")
        return

    # ==========================
    # GIT ADD
    # ==========================

    if not run_command(
        ["git", "add", "."],
        "Git Add"
    ):
        sys.exit(1)

    # ==========================
    # GIT COMMIT
    # ==========================

    if not run_command(
        [
            "git",
            "commit",
            "-m",
            COMMIT_MESSAGE
        ],
        "Git Commit"
    ):
        sys.exit(1)

    # ==========================
    # GIT PUSH
    # ==========================

    if not run_command(
        [
            "git",
            "push",
            "origin",
            GITHUB_BRANCH
        ],
        "Git Push"
    ):
        sys.exit(1)

    print(
        "\n✅ GitHub Updated Successfully!"
    )


if __name__ == "__main__":
    main()