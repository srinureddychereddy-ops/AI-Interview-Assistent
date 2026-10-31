"""
execution_engine.py — Secure Docker-based Code Execution Engine for Interview.ai
Phase 3 Production Implementation.

Runs candidate Python code inside an isolated, resource-constrained,
non-networked Docker container (`python:3.11-alpine`).
"""

import os
import json
import uuid
import time
import tempfile
import shutil
import subprocess
from typing import Dict, Any, List, Optional

import question_bank

_DOCKER_STATUS_CACHE = {"available": None, "checked_at": 0.0, "error": ""}


def check_docker_available(force: bool = False) -> tuple[bool, str]:
    """
    Verifies if Docker CLI exists and Docker daemon is responsive.
    Returns (True, "") if responsive.
    Returns (False, error_message) if Docker is missing or daemon cannot be reached.
    """
    now = time.time()
    if not force and _DOCKER_STATUS_CACHE["available"] is not None:
        if now - _DOCKER_STATUS_CACHE["checked_at"] < 3.0:
            return _DOCKER_STATUS_CACHE["available"], _DOCKER_STATUS_CACHE["error"]

    docker_bin = shutil.which("docker")
    if not docker_bin:
        _DOCKER_STATUS_CACHE["available"] = False
        _DOCKER_STATUS_CACHE["checked_at"] = now
        _DOCKER_STATUS_CACHE["error"] = "Docker executable not found on system PATH."
        return False, _DOCKER_STATUS_CACHE["error"]

    try:
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if proc.returncode == 0:
            _DOCKER_STATUS_CACHE["available"] = True
            _DOCKER_STATUS_CACHE["checked_at"] = now
            _DOCKER_STATUS_CACHE["error"] = ""
            return True, ""
        err = (proc.stderr or proc.stdout or "").strip()
        _DOCKER_STATUS_CACHE["available"] = False
        _DOCKER_STATUS_CACHE["checked_at"] = now
        _DOCKER_STATUS_CACHE["error"] = err or f"Docker daemon returned code {proc.returncode}"
        return False, _DOCKER_STATUS_CACHE["error"]
    except subprocess.TimeoutExpired:
        _DOCKER_STATUS_CACHE["available"] = False
        _DOCKER_STATUS_CACHE["checked_at"] = now
        _DOCKER_STATUS_CACHE["error"] = "Docker daemon connection timed out."
        return False, _DOCKER_STATUS_CACHE["error"]
    except Exception as e:
        _DOCKER_STATUS_CACHE["available"] = False
        _DOCKER_STATUS_CACHE["checked_at"] = now
        _DOCKER_STATUS_CACHE["error"] = str(e)
        return False, str(e)


# Canonical question definitions and test cases for fast lookup
QUESTION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "1": {
        "id": "1",
        "key": "two-sum",
        "title": "Two Sum",
        "function_name": "two_sum",
        "comparator": "unordered_list",
        "test_cases": [
            {"id": 1, "input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
            {"id": 2, "input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
            {"id": 3, "input": {"nums": [3, 3], "target": 6}, "expected": [0, 1]}
        ]
    },
    "2": {
        "id": "2",
        "key": "valid-palindrome",
        "title": "Valid Palindrome",
        "function_name": "is_palindrome",
        "comparator": "exact",
        "test_cases": [
            {"id": 1, "input": {"s": "A man, a plan, a canal: Panama"}, "expected": True},
            {"id": 2, "input": {"s": "race a car"}, "expected": False},
            {"id": 3, "input": {"s": " "}, "expected": True}
        ]
    }
}

QUESTION_REGISTRY["two-sum"] = QUESTION_REGISTRY["1"]
QUESTION_REGISTRY["valid-palindrome"] = QUESTION_REGISTRY["2"]


def resolve_question_metadata(question_id: str) -> Dict[str, Any]:
    """Resolves question metadata from question_bank or fallback QUESTION_REGISTRY."""
    q_str = str(question_id).strip()
    if q_str in question_bank.QUESTION_MAP:
        return question_bank.QUESTION_MAP[q_str]
    if q_str in QUESTION_REGISTRY:
        return QUESTION_REGISTRY[q_str]
    return QUESTION_REGISTRY.get("1")


RUNNER_SCRIPT = r'''
import sys
import json
import time
import io
import traceback
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Test case execution timed out (exceeded execution time limit).")

try:
    signal.signal(signal.SIGALRM, timeout_handler)
except Exception:
    pass

def compare_results(actual, expected, comparator):
    if comparator == "unordered_list":
        if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            try:
                return sorted(list(actual)) == sorted(list(expected))
            except Exception:
                return set(actual) == set(expected)
    elif comparator == "grouped_lists":
        if isinstance(actual, list) and isinstance(expected, list):
            try:
                norm_act = sorted([sorted(list(sub)) for sub in actual])
                norm_exp = sorted([sorted(list(sub)) for sub in expected])
                return norm_act == norm_exp
            except Exception:
                pass
    elif isinstance(actual, float) and isinstance(expected, (float, int)):
        return abs(actual - float(expected)) < 1e-2
    elif isinstance(expected, float) and isinstance(actual, (float, int)):
        return abs(float(actual) - expected) < 1e-2
    return actual == expected

def main():
    try:
        with open("tests.json", "r", encoding="utf-8") as f:
            test_config = json.load(f)
    except Exception as e:
        print(json.dumps({
            "status": "System Error",
            "passed": 0,
            "total": 0,
            "error": f"Failed to load test configuration: {str(e)}",
            "test_cases": [],
            "stdout": "",
            "stderr": str(e),
            "execution_time_ms": 0
        }))
        return

    function_name = test_config.get("function_name")
    comparator = test_config.get("comparator", "exact")
    test_cases = test_config.get("test_cases", [])
    total_tests = len(test_cases)

    # 1. Syntax & Import Check
    global_stdout = io.StringIO()
    global_stderr = io.StringIO()

    try:
        with open("solution.py", "r", encoding="utf-8") as f:
            code_str = f.read()
        compiled_code = compile(code_str, "solution.py", "exec")
    except SyntaxError as e:
        tb = traceback.format_exc()
        print(json.dumps({
            "status": "Syntax Error",
            "passed": 0,
            "total": total_tests,
            "error_type": "SyntaxError",
            "error": f"SyntaxError at line {e.lineno}: {e.msg}",
            "test_cases": [],
            "stdout": "",
            "stderr": tb,
            "execution_time_ms": 0
        }))
        return
    except Exception as e:
        tb = traceback.format_exc()
        print(json.dumps({
            "status": "Error",
            "passed": 0,
            "total": total_tests,
            "error_type": type(e).__name__,
            "error": str(e),
            "test_cases": [],
            "stdout": "",
            "stderr": tb,
            "execution_time_ms": 0
        }))
        return

    # Execute module scope
    module_globals = {"__name__": "__main__"}
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = global_stdout
    sys.stderr = global_stderr

    try:
        exec(compiled_code, module_globals)
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        tb = traceback.format_exc()
        print(json.dumps({
            "status": "Runtime Error",
            "passed": 0,
            "total": total_tests,
            "error_type": type(e).__name__,
            "error": f"{type(e).__name__}: {str(e)}",
            "test_cases": [],
            "stdout": global_stdout.getvalue(),
            "stderr": tb,
            "execution_time_ms": 0
        }))
        return
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    # Locate the target function - exact function name matching required
    target_func = module_globals.get(function_name)
    if not callable(target_func):
        print(json.dumps({
            "status": "Runtime Error",
            "passed": 0,
            "total": total_tests,
            "error_type": "NameError",
            "error": f"Function '{function_name}' not defined in solution. Expected function name: def {function_name}(...).",
            "test_cases": [],
            "stdout": global_stdout.getvalue(),
            "stderr": f"NameError: Function '{function_name}' not found. Please implement 'def {function_name}(...)'.",
            "execution_time_ms": 0
        }))
        return

    # 2. Run Test Cases
    results = []
    passed_count = 0
    start_total_time = time.perf_counter()

    for idx, tc in enumerate(test_cases, 1):
        tc_id = tc.get("id", idx)
        tc_input = tc.get("input", {})
        tc_expected = tc.get("expected")
        is_hidden = tc.get("is_hidden", False)

        tc_stdout = io.StringIO()
        tc_stderr = io.StringIO()
        sys.stdout = tc_stdout
        sys.stderr = tc_stderr

        t0 = time.perf_counter()
        tc_error = None
        tc_error_type = None
        actual_val = None
        status = "Failed"

        try:
            try:
                signal.alarm(2)
            except Exception:
                pass

            if isinstance(tc_input, dict):
                actual_val = target_func(**tc_input)
            elif isinstance(tc_input, (list, tuple)):
                actual_val = target_func(*tc_input)
            else:
                actual_val = target_func(tc_input)

            try:
                signal.alarm(0)
            except Exception:
                pass

            if compare_results(actual_val, tc_expected, comparator):
                status = "Passed"
                passed_count += 1
            else:
                status = "Failed"

        except TimeoutError as e:
            try:
                signal.alarm(0)
            except Exception:
                pass
            status = "Timeout"
            tc_error_type = "TimeoutError"
            tc_error = "Test case execution timed out (exceeded 2.0s limit). Check for infinite loops or non-terminating recursion."
            tc_stderr.write("TimeoutError: Test case execution timed out.\n")
        except Exception as e:
            try:
                signal.alarm(0)
            except Exception:
                pass
            status = "Runtime Error"
            tc_error_type = type(e).__name__
            tc_error = f"{type(e).__name__}: {str(e)}"
            tc_stderr.write(traceback.format_exc())
        finally:
            t1 = time.perf_counter()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        results.append({
            "test_case_id": tc_id,
            "status": status,
            "input": json.dumps(tc_input),
            "expected": json.dumps(tc_expected),
            "actual": json.dumps(actual_val) if actual_val is not None else None,
            "stdout": tc_stdout.getvalue(),
            "stderr": tc_stderr.getvalue(),
            "error_type": tc_error_type,
            "error": tc_error,
            "is_hidden": is_hidden,
            "execution_time_ms": round((t1 - t0) * 1000, 2)
        })

    total_time_ms = round((time.perf_counter() - start_total_time) * 1000, 2)

    if passed_count == total_tests:
        overall_status = "Passed"
    elif any(r["status"] == "Timeout" for r in results):
        overall_status = "Timeout"
    elif any(r["status"] == "Runtime Error" for r in results) and passed_count == 0:
        overall_status = "Runtime Error"
    else:
        overall_status = "Failed"

    stdout_full = global_stdout.getvalue()
    if not stdout_full:
        tc_prints = [f"--- Test Case {r['test_case_id']} Output ---\n{r['stdout'].strip()}" for r in results if r['stdout'].strip()]
        if tc_prints:
            stdout_full = "\n\n".join(tc_prints)

    print(json.dumps({
        "status": overall_status,
        "passed": passed_count,
        "total": total_tests,
        "test_cases": results,
        "stdout": stdout_full,
        "stderr": global_stderr.getvalue(),
        "execution_time_ms": total_time_ms
    }))

if __name__ == "__main__":
    main()
'''


def execute_python_code(
    code: str,
    question_id: str = "1",
    custom_test_cases: Optional[List[Dict[str, Any]]] = None,
    function_name: Optional[str] = None,
    comparator: Optional[str] = None,
    timeout_seconds: int = 15
) -> Dict[str, Any]:
    """
    Executes Python source code in an isolated Docker container.
    Distinguishes Docker infrastructure failures from candidate code execution.
    """
    if not code or not code.strip():
        return {
            "status": "Error",
            "passed": 0,
            "total": 0,
            "error": "No code provided for execution.",
            "test_cases": [],
            "stdout": "",
            "stderr": "Submission was empty.",
            "execution_time_ms": 0,
            "is_infrastructure_error": False
        }

    # 1. Verify Docker availability before executing
    is_docker_ok, docker_err = check_docker_available()
    if not is_docker_ok:
        return {
            "status": "Execution Unavailable",
            "passed": 0,
            "total": len(custom_test_cases or []),
            "error_type": "execution_environment",
            "error": "Code execution environment is currently unavailable. Docker sandbox could not be reached.",
            "test_cases": [],
            "stdout": "",
            "stderr": docker_err,
            "execution_time_ms": 0,
            "is_infrastructure_error": True
        }

    q_meta = resolve_question_metadata(question_id)
    fn_name = function_name or q_meta.get("function_name", "solution")
    comp = comparator or q_meta.get("comparator", "exact")

    if custom_test_cases and isinstance(custom_test_cases, list) and len(custom_test_cases) > 0 and isinstance(custom_test_cases[0].get("input"), (dict, list)):
        test_cases = custom_test_cases
    else:
        test_cases = q_meta.get("test_cases", [])

    test_config = {
        "function_name": fn_name,
        "comparator": comp,
        "test_cases": test_cases
    }

    container_id = f"sandbox_{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory() as temp_dir:
        solution_path = os.path.join(temp_dir, "solution.py")
        tests_path = os.path.join(temp_dir, "tests.json")
        runner_path = os.path.join(temp_dir, "runner.py")

        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(tests_path, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(RUNNER_SCRIPT)

        mount_path = os.path.abspath(temp_dir).replace('\\', '/')

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", container_id,
            "--network", "none",
            "--cpus", "0.5",
            "-m", "128m",
            "--memory-swap", "128m",
            "--pids-limit", "64",
            "-v", f"{mount_path}:/sandbox:ro",
            "-w", "/sandbox",
            "python:3.11-alpine",
            "python", "runner.py"
        ]

        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            stdout = proc.stdout.strip() if proc.stdout else ""
            stderr = proc.stderr.strip() if proc.stderr else ""

            if stdout:
                try:
                    data = json.loads(stdout)
                    if "execution_time_ms" not in data or data["execution_time_ms"] == 0:
                        data["execution_time_ms"] = elapsed_ms
                    data["is_infrastructure_error"] = False
                    return data
                except json.JSONDecodeError:
                    pass

            # Detect Docker daemon or pipe connection infrastructure errors
            is_infra_err = any(phrase in stderr.lower() for phrase in [
                "failed to connect to the docker api",
                "cannot connect to the docker daemon",
                "error during connect",
                "docker daemon is not running",
                "is the docker daemon running",
                "npipe"
            ])
            if is_infra_err:
                return {
                    "status": "Execution Unavailable",
                    "passed": 0,
                    "total": len(test_cases),
                    "error_type": "execution_environment",
                    "error": "Code execution environment is currently unavailable. Docker engine failed to respond.",
                    "test_cases": [],
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": elapsed_ms,
                    "is_infrastructure_error": True
                }

            if proc.returncode != 0:
                if proc.returncode == 137:
                    return {
                        "status": "Memory Limit Exceeded",
                        "passed": 0,
                        "total": len(test_cases),
                        "error_type": "MemoryLimitExceeded",
                        "error": "Memory limit exceeded (128MB limit).",
                        "test_cases": [],
                        "stdout": stdout,
                        "stderr": "Process killed: out of memory.",
                        "execution_time_ms": elapsed_ms,
                        "is_infrastructure_error": False
                    }

                return {
                    "status": "Runtime Error",
                    "passed": 0,
                    "total": len(test_cases),
                    "error_type": "ProcessError",
                    "error": stderr or f"Process exited with code {proc.returncode}",
                    "test_cases": [],
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": elapsed_ms,
                    "is_infrastructure_error": False
                }

            return {
                "status": "Success",
                "passed": len(test_cases),
                "total": len(test_cases),
                "test_cases": [],
                "stdout": stdout,
                "stderr": stderr,
                "execution_time_ms": elapsed_ms,
                "is_infrastructure_error": False
            }

        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "Timeout",
                "passed": 0,
                "total": len(test_cases),
                "error_type": "TimeoutError",
                "error": f"Execution timed out (exceeded {timeout_seconds}s limit). Check for infinite loops or non-terminating recursion.",
                "test_cases": [],
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "execution_time_ms": elapsed_ms,
                "is_infrastructure_error": False
            }

        except Exception as e:
            subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "System Error",
                "passed": 0,
                "total": len(test_cases),
                "error_type": type(e).__name__,
                "error": f"Internal execution engine error: {str(e)}",
                "test_cases": [],
                "stdout": "",
                "stderr": str(e),
                "execution_time_ms": elapsed_ms,
                "is_infrastructure_error": True
            }


def evaluate_question_submission(
    code: str,
    question_data: Dict[str, Any],
    timeout_seconds: int = 15
) -> Dict[str, Any]:
    """
    Evaluates candidate solution against BOTH visible and hidden test cases in Docker.
    Returns full test case breakdown, visible/hidden stats, and deterministic score.
    """
    q_id = question_data.get("id", "1")
    title = question_data.get("title", "Question")
    difficulty = question_data.get("difficulty", "Medium")
    time_comp = question_data.get("time_complexity", "O(n)")
    space_comp = question_data.get("space_complexity", "O(1)")
    fn_name = question_data.get("function_name")
    comp = question_data.get("comparator", "exact")

    # Prepare visible and hidden test cases
    visible_tests = copy_and_tag_tests(question_data.get("test_cases", []), is_hidden=False)
    hidden_tests = copy_and_tag_tests(question_data.get("hidden_test_cases", []), is_hidden=True)
    all_tests = visible_tests + hidden_tests
    vis_total = len(visible_tests)
    hid_total = len(hidden_tests)
    tot_tests = len(all_tests)

    # Check for empty code
    if not code or not code.strip() or code.strip() == "pass":
        return {
            "question_id": q_id,
            "title": title,
            "difficulty": difficulty,
            "status": "Not Attempted",
            "submitted_code": code or "",
            "score": 0.0,
            "visible_passed": 0,
            "visible_total": vis_total,
            "hidden_passed": 0,
            "hidden_total": hid_total,
            "total_passed": 0,
            "total_test_cases": tot_tests,
            "execution_time_ms": 0.0,
            "time_complexity": time_comp,
            "space_complexity": space_comp,
            "code_quality_note": "No solution submitted for this problem.",
            "test_cases": [],
            "is_infrastructure_error": False
        }

    # Execute in Docker sandbox using explicit function name
    run_res = execute_python_code(
        code=code,
        question_id=q_id,
        custom_test_cases=all_tests,
        function_name=fn_name,
        comparator=comp,
        timeout_seconds=timeout_seconds
    )

    tc_results = run_res.get("test_cases", [])

    # Check for infrastructure failure
    if run_res.get("is_infrastructure_error") or run_res.get("status") == "Execution Unavailable":
        return {
            "question_id": q_id,
            "title": title,
            "difficulty": difficulty,
            "status": "Execution Unavailable",
            "submitted_code": code,
            "score": 0.0,
            "test_case_score": 0.0,
            "efficiency_score": 0.0,
            "correctness_score": 0.0,
            "quality_score": 0.0,
            "visible_passed": 0,
            "visible_total": vis_total,
            "hidden_passed": 0,
            "hidden_total": hid_total,
            "total_passed": 0,
            "total_test_cases": tot_tests,
            "execution_time_ms": run_res.get("execution_time_ms", 0.0),
            "time_complexity": time_comp,
            "space_complexity": space_comp,
            "code_quality_note": "Code evaluation could not be completed because the execution environment was unavailable.",
            "error": run_res.get("error"),
            "error_type": "execution_environment",
            "stdout": run_res.get("stdout"),
            "stderr": run_res.get("stderr"),
            "test_cases": tc_results,
            "is_infrastructure_error": True
        }

    # Separate visible vs hidden results
    vis_passed = sum(1 for tc in tc_results if not tc.get("is_hidden") and tc.get("status") == "Passed")
    hid_passed = sum(1 for tc in tc_results if tc.get("is_hidden") and tc.get("status") == "Passed")
    tot_passed = run_res.get("passed", 0)

    # Compute deterministic score
    scoring = question_bank.score_question(code, run_res)

    quality_note = "Clean implementation."
    if scoring["status"] == "Solved":
        quality_note = f"All test cases passed cleanly with optimal efficiency ({run_res.get('execution_time_ms', 0)} ms)."
    elif scoring["status"] == "Partially Solved":
        quality_note = f"Passed {tot_passed} of {tot_tests} test cases. Review edge cases."
    elif run_res.get("status") == "Syntax Error":
        quality_note = f"Syntax error occurred: {run_res.get('error')}"
    elif run_res.get("status") == "Timeout":
        quality_note = "Execution timed out. Optimize algorithm complexity to avoid infinite loops."
    elif run_res.get("status") == "Runtime Error":
        quality_note = f"Runtime error: {run_res.get('error')}"
    else:
        quality_note = "Solution encountered incorrect logic on test cases."

    return {
        "question_id": q_id,
        "title": title,
        "difficulty": difficulty,
        "status": scoring["status"],
        "submitted_code": code,
        "score": scoring["score"],
        "test_case_score": scoring["test_case_score"],
        "efficiency_score": scoring["efficiency_score"],
        "correctness_score": scoring["correctness_score"],
        "quality_score": scoring["quality_score"],
        "visible_passed": vis_passed,
        "visible_total": vis_total,
        "hidden_passed": hid_passed,
        "hidden_total": hid_total,
        "total_passed": tot_passed,
        "total_test_cases": tot_tests,
        "execution_time_ms": run_res.get("execution_time_ms", 0.0),
        "time_complexity": time_comp,
        "space_complexity": space_comp,
        "code_quality_note": quality_note,
        "error": run_res.get("error"),
        "error_type": run_res.get("error_type"),
        "stdout": run_res.get("stdout"),
        "stderr": run_res.get("stderr"),
        "test_cases": tc_results,
        "is_infrastructure_error": False
    }


def copy_and_tag_tests(tests: List[Dict[str, Any]], is_hidden: bool) -> List[Dict[str, Any]]:
    res = []
    for t in tests:
        tc = dict(t)
        tc["is_hidden"] = is_hidden
        res.append(tc)
    return res


def evaluate_full_assessment(
    submitted_answers: Dict[str, str],
    questions: List[Dict[str, Any]],
    time_used_seconds: int = 0
) -> Dict[str, Any]:
    """
    Evaluates all submitted solutions in Docker containers and returns full assessment summary.
    """
    results_per_question = []
    total_score_sum = 0.0
    questions_solved = 0
    questions_attempted = 0
    total_tests_sum = 0
    passed_tests_sum = 0
    failed_tests_sum = 0
    execution_errors_count = 0

    for idx, q in enumerate(questions, 1):
        q_id = str(q.get("id"))
        # Candidate code could be stored by q_id or index string
        code = submitted_answers.get(q_id)
        if code is None:
            code = submitted_answers.get(str(idx), "")

        if code and str(code).strip():
            questions_attempted += 1

        eval_res = evaluate_question_submission(code, q)
        results_per_question.append(eval_res)

        total_score_sum += eval_res["score"]
        if eval_res["status"] == "Solved":
            questions_solved += 1
        if eval_res.get("error"):
            execution_errors_count += 1

        total_tests_sum += eval_res["total_test_cases"]
        passed_tests_sum += eval_res["total_passed"]
        failed_tests_sum += (eval_res["total_test_cases"] - eval_res["total_passed"])

    total_q_count = len(questions) or 1
    overall_score = round(total_score_sum / total_q_count)
    has_infrastructure_error = any(r.get("is_infrastructure_error") for r in results_per_question)

    return {
        "overall_score": overall_score,
        "questions_count": len(questions),
        "questions_attempted": questions_attempted,
        "questions_solved": questions_solved,
        "questions_partially_solved": sum(1 for r in results_per_question if r["status"] == "Partially Solved"),
        "questions_unsolved": sum(1 for r in results_per_question if r["status"] in ["Not Solved", "Not Attempted"]),
        "has_infrastructure_error": has_infrastructure_error,
        "total_test_cases": total_tests_sum,
        "passed_test_cases": passed_tests_sum,
        "failed_test_cases": failed_tests_sum,
        "execution_errors": execution_errors_count,
        "time_used_seconds": time_used_seconds,
        "results": results_per_question
    }
