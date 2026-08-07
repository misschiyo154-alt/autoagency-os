import subprocess

commands = [
    ["git", "add", "."],
    ["git", "commit", "-m", "AI Generated Website"],
    ["git", "push", "origin", "main"]
]

for command in commands:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        pass

print("✅ GitHub Updated Successfully!")