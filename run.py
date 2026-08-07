import subprocess

print("🚀 Starting AI Agency...\n")

subprocess.run(["python", "08-scripts/generate_website.py"])

subprocess.run(["python", "08-scripts/git_push.py"])

print("\n✅ Everything Finished Successfully!")