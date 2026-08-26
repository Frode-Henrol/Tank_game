"""
Step through the curated devlog commit history and run each version of the game.

Usage:
    python devlog_runner.py            # resume where you left off (or start at #1)
    python devlog_runner.py --restart  # ignore saved progress, start over from #1

While running:
    [Enter]  check out this commit and launch the game (waits for you to close it)
    s        skip this commit without running it
    b        go back one commit
    j <n>    jump to commit number n (see 'l' for the list)
    l        list all commits with their numbers
    q        save progress and quit
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
WORKTREE_DIR = REPO_DIR.parent / "Tank_game_devlog_runner"
COMMITS_FILE = REPO_DIR / "devlog_commits.json"
STATE_FILE = REPO_DIR / ".devlog_runner_state.json"


def load_commits():
    with open(COMMITS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f).get("index", 0)
    return 0


def save_state(index):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"index": index}, f)


def find_python():
    for candidate in (["py", "-3.12"], ["python3.12"], ["python"]):
        if shutil.which(candidate[0]):
            return candidate
    print("Could not find a Python interpreter on PATH.")
    sys.exit(1)


def checkout(commit_hash):
    subprocess.run(["git", "-C", str(WORKTREE_DIR), "clean", "-fdx"], capture_output=True)
    result = subprocess.run(
        ["git", "-C", str(WORKTREE_DIR), "checkout", "--force", commit_hash],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  git checkout failed:\n{result.stderr}")
        return False
    return True


def detect_command(python_cmd):
    if (WORKTREE_DIR / "tankgame" / "__main__.py").exists():
        return python_cmd + ["-m", "tankgame"]
    if (WORKTREE_DIR / "main.py").exists():
        return python_cmd + ["main.py"]
    return None


def clean(text):
    return text.replace("—", "-")


def print_entry(i, total, entry):
    print()
    print(f"[{i + 1}/{total}] {entry['date']}  {entry['hash']}  - {clean(entry['chapter'])}")
    print(f"    \"{entry['subject']}\"")
    if entry.get("note"):
        print(f"    note: {entry['note']}")


def list_commits(commits):
    for i, entry in enumerate(commits):
        print(f"{i + 1:>3}  {entry['date']}  {entry['hash']}  {entry['subject']}  [{clean(entry['chapter'])}]")


def main():
    if not WORKTREE_DIR.exists():
        print(f"Worktree not found at {WORKTREE_DIR}.")
        print('Create it once with: git worktree add "../Tank_game_devlog_runner" <first-commit-hash>')
        sys.exit(1)

    commits = load_commits()
    total = len(commits)
    python_cmd = find_python()

    restart = "--restart" in sys.argv
    i = 0 if restart else load_state()
    i = max(0, min(i, total - 1))

    if not restart and i > 0:
        print(f"Resuming from #{i + 1}/{total} ({commits[i]['hash']} — {commits[i]['subject']})")
        print("(run with --restart to start over from #1)")

    while 0 <= i < total:
        entry = commits[i]
        print_entry(i, total, entry)

        choice = input("[Enter]=run  s=skip  b=back  j <n>=jump  l=list  q=quit > ").strip().lower()

        if choice == "q":
            save_state(i)
            print("Progress saved. Resume any time with: python devlog_runner.py")
            break
        elif choice == "l":
            list_commits(commits)
            continue
        elif choice == "s":
            i += 1
            save_state(i)
            continue
        elif choice == "b":
            i = max(0, i - 1)
            save_state(i)
            continue
        elif choice.startswith("j"):
            parts = choice.split()
            if len(parts) == 2 and parts[1].isdigit():
                i = max(0, min(int(parts[1]) - 1, total - 1))
                save_state(i)
            else:
                print("  usage: j <number>")
            continue
        else:
            if not checkout(entry["hash"]):
                continue
            cmd = detect_command(python_cmd)
            if cmd is None:
                print("  Could not find an entry point (no tankgame/__main__.py or main.py) — skipping.")
                i += 1
                save_state(i)
                continue
            print(f"  Launching: {' '.join(cmd)}   (close the game window to continue)")
            result = subprocess.run(cmd, cwd=str(WORKTREE_DIR))
            if result.returncode != 0:
                print(f"  (process exited with code {result.returncode} — may have crashed)")
            i += 1
            save_state(i)
    else:
        print()
        print("Reached the end of the list — that's present day.")


if __name__ == "__main__":
    main()
