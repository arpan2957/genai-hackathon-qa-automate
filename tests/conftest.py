import pytest
import subprocess
import os
import signal
import time

@pytest.fixture(scope="session", autouse=True)
def start_servers():
    # Helper function to kill processes on a given port
    def kill_process_on_port(port):
        try:
            # Find PIDs listening on the port
            pids = subprocess.check_output(["lsof", "-ti", f":{port}"]).decode().strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Killing process {pid} on port {port}")
                    subprocess.run(["kill", "-9", pid])
                    time.sleep(1) # Give time for the process to terminate
        except subprocess.CalledProcessError:
            # No process found on the port
            pass
        except Exception as e:
            print(f"Error killing process on port {port}: {e}")

    print("Ensuring clean environment before tests...")
    kill_process_on_port(3000) # Frontend port
    kill_process_on_port(8000) # Backend port
    print("Environment cleaned.")

    # Install backend dependencies
    print("Installing backend dependencies...")
    subprocess.run(
        ["pip3", "install", "-r", "backend/requirements.txt"],
        check=True
    )

    # Install frontend dependencies
    print("Installing frontend dependencies...")
    subprocess.run(
        ["npm", "install"],
        cwd="frontend",
        check=True
    )

    # Start backend server
    print("Starting backend server...")
    backend_env = os.environ.copy()
    if "PYTEST_CURRENT_TEST" in backend_env:
        del backend_env["PYTEST_CURRENT_TEST"]
    backend_process = subprocess.Popen(
        ["python3", "-m", "uvicorn", "main:app", "--reload"],
        cwd="backend",
        preexec_fn=os.setsid,
        env=backend_env
    )
    backend_pgid = os.getpgid(backend_process.pid)
    print(f"Backend server started with PGID: {backend_pgid}")

    # Start frontend server
    print("Starting frontend server...")
    frontend_process = subprocess.Popen(
        ["npm", "start"],
        cwd="frontend",
        preexec_fn=os.setsid,
        env=os.environ
    )
    frontend_pgid = os.getpgid(frontend_process.pid)
    print(f"Frontend server started with PGID: {frontend_pgid}")

    # Wait for servers to initialize
    print("Waiting for servers to initialize (30 seconds)...")
    time.sleep(30)

    yield

    # Teardown: Kill server processes
    print("\nCleaning up server processes...")
    try:
        if backend_pgid:
            os.killpg(backend_pgid, signal.SIGTERM)
            print(f"Killed backend process group {backend_pgid}")
        if frontend_pgid:
            os.killpg(frontend_pgid, signal.SIGTERM)
            print(f"Killed frontend process group {frontend_pgid}")
    except ProcessLookupError:
        pass # Process already terminated
    print("Cleanup complete.")


