from config import *
import subprocess

commands = [
    ["git", "add", "."],
    ["git", "commit", "-m", "COMMIT_MESSAGE"],
    ["git", "push", "origin", "main"]
]

for command in commands:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        pass

print("✅ GitHub Updated Successfully!")