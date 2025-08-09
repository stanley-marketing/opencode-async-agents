#!/usr/bin/env python3
import subprocess
import time
import requests
import os
from pathlib import Path

SERVER_PORT = int(os.environ.get("PORT", 8099))
SERVER_URL = f"http://localhost:{SERVER_PORT}"


def wait_for_server(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{SERVER_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    env = os.environ.copy()
    env["OPENCODE_SAFE_MODE"] = "true"

    server = subprocess.Popen([
        "python3", "-m", "src.server", "--port", str(SERVER_PORT)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

    try:
        print("Starting server...")
        assert wait_for_server(), "server failed to start"
        print("Server started successfully")

        r = requests.get(f"{SERVER_URL}/employees")
        assert r.status_code == 200
        employees = r.json()["employees"]
        print(f"Current employees: {[e['name'] for e in employees]}")
        
        if not any(e["name"] == "wet-worker" for e in employees):
            print("Hiring wet-worker...")
            r = requests.post(f"{SERVER_URL}/employees", json={"name": "wet-worker", "role": "developer"})
            assert r.status_code == 200
            print("wet-worker hired successfully")

        task = "Run ruff lint on the src directory and write the full results to ./tmp/lint_result.md, then summarize in your final message"
        print(f"Assigning task: {task}")
        r = requests.post(f"{SERVER_URL}/tasks", json={"name": "wet-worker", "task": task, "model": "test-model"})
        assert r.status_code == 200
        data = r.json()
        print(f"Task assignment response: {data}")
        assert "Started task" in data.get("message", "")
        session_id = data.get("session_id")
        assert session_id
        print(f"Session started: {session_id}")

        # poll status until no active sessions
        print("Waiting for task completion...")
        deadline = time.time() + 3600
        while time.time() < deadline:
            r = requests.get(f"{SERVER_URL}/sessions")
            assert r.status_code == 200
            sessions = r.json().get("sessions", {})
            if "wet-worker" not in sessions:
                print("Task completed!")
                break
            print(f"Still running... sessions: {list(sessions.keys())}")
            time.sleep(2)
        else:
            raise RuntimeError("task did not complete in time")

        # inspect all artifacts
        print("Inspecting artifacts...")
        sessions_dir = Path("sessions") / "wet-worker"
        content = ""
        if sessions_dir.exists():
            print(f"Sessions dir exists: {sessions_dir}")
            logs = sorted(sessions_dir.glob("session_*.log"))
            print(f"Found {len(logs)} session logs")
            for p in logs:
                try:
                    log_content = p.read_text(errors="ignore")
                    content += log_content
                    print(f"Log {p.name}: {len(log_content)} chars")
                except Exception as e:
                    print(f"Error reading {p}: {e}")
            
            task_files = list(sessions_dir.glob("*.md"))
            print(f"Found {len(task_files)} task files")
            for p in task_files:
                try:
                    task_content = p.read_text(errors="ignore")
                    content += "\n" + task_content
                    print(f"Task file {p.name}: {len(task_content)} chars")
                except Exception as e:
                    print(f"Error reading {p}: {e}")
        else:
            print("Sessions dir does not exist")

        # check tracker files
        tracker_dir = Path("sessions") / "progress" / "wet-worker"
        if tracker_dir.exists():
            print(f"Tracker dir exists: {tracker_dir}")
            for p in tracker_dir.rglob("*"):
                if p.is_file():
                    try:
                        tracker_content = p.read_text(errors="ignore")
                        content += "\n" + tracker_content
                        print(f"Tracker file {p.name}: {len(tracker_content)} chars")
                    except Exception as e:
                        print(f"Error reading tracker {p}: {e}")
        else:
            print("Tracker dir does not exist")

        # check explicit artifact
        artifact = Path("tmp/lint_result.md")
        if artifact.exists():
            print(f"Lint artifact exists: {artifact.stat().st_size} bytes")
            artifact_content = artifact.read_text(errors="ignore")
            content += "\n" + artifact_content
            print(f"Artifact content preview: {artifact_content[:200]}...")
        else:
            print("Lint artifact does not exist")

        print(f"Total content collected: {len(content)} chars")
        if content:
            low = content.lower()
            has_lint = "lint" in low or "ruff" in low or "error" in low or "warning" in low
            print(f"Contains lint evidence: {has_lint}")
            
            # Also check that completion message includes lint results
            has_completion_with_lint = ("task completed" in low or "completed" in low) and ("e302" in low or "e501" in low or "f401" in low)
            print(f"Contains completion message with lint details: {has_completion_with_lint}")
            
            if has_lint and has_completion_with_lint:
                print("OK: lint evidence found and completion message includes lint details")
            elif has_lint:
                print("PARTIAL: lint evidence found but completion message missing lint details")
                print(f"Content preview: {content[:1000]}...")
                raise AssertionError("completion message should include lint results")
            else:
                print("FAIL: no lint evidence in content")
                print(f"Content preview: {content[:500]}...")
                raise AssertionError("lint output not found in artifacts")
        else:
            print("FAIL: no content found at all")
            raise AssertionError("no artifacts found")

    finally:
        print("Shutting down server...")
        try:
            server.terminate()
            stdout, stderr = server.communicate(timeout=10)
            if stdout:
                print(f"Server stdout:\n{stdout}")
            if stderr:
                print(f"Server stderr:\n{stderr}")
        except Exception as e:
            print(f"Error getting server output: {e}")
            server.kill()


if __name__ == "__main__":
    main()
