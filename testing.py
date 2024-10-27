tests = [
    {
        "input": "hello",
        "output": "hello",
        "time_limit": 1
    },
    {
        "input": "hello",
        "output": "hello",
        "time_limit": 1
    }
]

import subprocess
import os


def check_docker_daemon():
    try:
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Docker is running.")
    except subprocess.CalledProcessError:
        raise RuntimeError("Docker daemon is not running. Please start Docker and try again.")


def prepare_container(language, path):
    container_image = "python:3.11" if language == "python" else "gcc:latest"
    subprocess.run(["docker", "pull", container_image], check=True)

    volume_binding = f"{path}:/code"
    print(volume_binding)
    container_id = subprocess.run(
        ["docker", "run", "-d", "-v", volume_binding, container_image, "sleep", "infinity"],
        check=True,
        stdout=subprocess.PIPE
    ).stdout.decode().strip()

    # Show the contents of /code directory in the container
    ls_result = subprocess.run(
        ["docker", "exec", container_id, "ls", "/code"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print("Contents of /code directory in the container:")
    print(ls_result.stdout.decode())

    return container_id


def kill_container(container_id):
    subprocess.run(["docker", "kill", container_id])
    subprocess.run(["docker", "rm", container_id])


def prepare_execution(container_id, language):
    if language == "python":
        requirements_path = "/code/requirements.txt"
        if os.path.exists("./code/requirements.txt"):
            subprocess.run(
                ["docker", "exec", container_id, "pip", "install", "-r", requirements_path],
                check=True
            )

    if language == "cpp":
        compile_command = f"g++ /code/{script} -o /code/program"
        compile_result = subprocess.run(
            ["docker", "exec", container_id, "bash", "-c", compile_command],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if compile_result.returncode != 0:
            raise f"Compilation failed: {compile_result.stderr.decode()}"


def execute_test(container_id, script, test):
    input_data = test['input']
    expected_output = test['output']
    time_limit = test['time_limit']
    memory_limit = test['memory_limit']

    if language == "python":
        exec_command = f"python3 /code/{script}"
    else:
        exec_command = f"./code/program"

    print(exec_command)

    try:
        exec_result = subprocess.run(
            ["docker", "exec", "-i", container_id, "bash", "-c", exec_command],
            input=input_data.encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=time_limit
        )
        output = exec_result.stdout.decode().strip()

        if output == expected_output:
            print(f"Test passed: {input_data}")
        else:
            print(f"Test failed: {input_data} - Expected: {expected_output}, Got: {output}")

    except subprocess.TimeoutExpired:
        print(f"Test failed: Execution timed out after {time_limit} seconds.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")


def run_tests_in_docker(language, folder, script, test_cases):
    try:
        check_docker_daemon()
    except Exception as e:
        print(f"Error checking Docker daemon: {e}")
        return

    container_id = prepare_container(language, folder)

    if container_id:
        try:
            prepare_execution(container_id, language)

            for test in test_cases:
                execute_test(container_id, script, test)

        finally:
            kill_container(container_id)


# Example usage
script = "test.py"  # or .cpp for C++ code
language = "python"  # or "cpp"
run_tests_in_docker(language, os.path.abspath("./code"), script, tests)
