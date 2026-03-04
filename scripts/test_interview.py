#!/usr/bin/env python3
"""
Generic API-driven interview test runner for docassemble.

Drives interviews through the docassemble REST API using test scenarios
defined in JSON files. Form-agnostic: works with any docassemble interview.
Add a new form by creating a JSON scenario file in scripts/test_scenarios/.

How it works:
  1. Reads scenario JSON files from scripts/test_scenarios/
  2. For each scenario, creates a fresh interview session via the API
  3. Adaptively answers whatever the interview asks, using the scenario's
     test data dictionary to look up values for each field
  4. Continues until the interview reaches a terminal screen or errors out
  5. Reports PASS/FAIL for each scenario

Usage:
    python scripts/test_interview.py                          # All scenarios
    python scripts/test_interview.py --scenario short_minimal # Specific scenario
    python scripts/test_interview.py --list                   # List scenarios
    python scripts/test_interview.py --verbose                # Show every step
    python scripts/test_interview.py --debug                  # Dump raw API JSON

Server config (any docassemble server — local Docker or remote):
    python scripts/test_interview.py --server http://localhost:5050  # Local Docker
    python scripts/test_interview.py --server https://my-server.com  # Remote server
    # Or set DA_SERVER and DA_API_KEY in scripts/.env
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCENARIOS_DIR = SCRIPT_DIR / "test_scenarios"
ENV_FILE = SCRIPT_DIR / ".env"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_env():
    """Load server URL and API key from environment variables or .env file.

    Priority: environment variables > CLI args > .env file.
    """
    import os

    # Check environment variables first (for CI environments like GitHub Actions)
    server = os.environ.get("DA_SERVER_URL", "") or os.environ.get("DA_SERVER", "")
    api_key = os.environ.get("DA_API_KEY", "")

    if server and api_key:
        return server, api_key

    # Fall back to .env file
    if ENV_FILE.exists():
        config = {}
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
        server = server or config.get("DA_SERVER", "")
        api_key = api_key or config.get("DA_API_KEY", "")
        return server, api_key

    # No config found
    print(f"{YELLOW}No server configuration found.{RESET}")
    print(f"  Set DA_SERVER_URL and DA_API_KEY environment variables (CI),")
    print(f"  or create {ENV_FILE} (local development),")
    print(f"  or use --server and --api-key flags.")
    return "", ""


def load_scenarios(filter_name=None):
    """Load all scenario JSON files from the test_scenarios directory."""
    if not SCENARIOS_DIR.exists():
        print(f"{RED}No test_scenarios directory at {SCENARIOS_DIR}{RESET}")
        return []

    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        if path.name.startswith(".") or path.name.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text())
            data["_file"] = path.name
            data["_path"] = str(path)
            if filter_name and filter_name not in path.stem:
                continue
            scenarios.append(data)
        except json.JSONDecodeError as e:
            print(f"{YELLOW}WARNING: Invalid JSON in {path.name}: {e}{RESET}")

    return scenarios


# ---------------------------------------------------------------------------
# Docassemble API Client
# ---------------------------------------------------------------------------

class DocassembleClient:
    """Lightweight client for the docassemble REST API."""

    def __init__(self, server, api_key):
        self.server = server.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()

    def health_check(self):
        """Check if the server is reachable."""
        try:
            r = self.session.get(f"{self.server}/health_check", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def new_session(self, interview_path):
        """Create a new interview session. Returns (session_id, secret, i).

        Note: 'secret' may not be present in the response when using an
        admin API key or when server-side encryption is not enabled.
        """
        r = self.session.get(
            f"{self.server}/api/session/new",
            params={"key": self.api_key, "i": interview_path},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data["session"], data.get("secret", ""), data.get("i", interview_path)

    def get_question(self, session_id, secret, i):
        """Get the current question screen. Returns full question JSON."""
        params = {
            "key": self.api_key,
            "i": i,
            "session": session_id,
        }
        if secret:
            params["secret"] = secret
        r = self.session.get(
            f"{self.server}/api/session/question",
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def set_variables(self, session_id, secret, i, variables):
        """Set interview variables and advance. Returns next question JSON."""
        payload = {
            "key": self.api_key,
            "i": i,
            "session": session_id,
            "variables": json.dumps(variables),
        }
        if secret:
            payload["secret"] = secret
        r = self.session.post(
            f"{self.server}/api/session",
            data=payload,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def delete_session(self, session_id, secret, i):
        """Clean up a session."""
        try:
            payload = {
                "key": self.api_key,
                "i": i,
                "session": session_id,
            }
            if secret:
                payload["secret"] = secret
            self.session.delete(
                f"{self.server}/api/session",
                data=payload,
                timeout=10,
            )
        except Exception:
            pass  # Best effort cleanup


# ---------------------------------------------------------------------------
# Adaptive Interview Driver
# ---------------------------------------------------------------------------

# Default values for field types when test data doesn't have a specific value
TYPE_DEFAULTS = {
    "text": "Test",
    "area": "Test text area content",
    "currency": 100,
    "number": 1,
    "integer": 1,
    "date": "2025-01-15",
    "email": "test@example.com",
    "yesno": True,
    "yesnowide": True,
    "yesnoradio": True,
    "noyes": False,
    "noyeswide": False,
    "noyesradio": False,
    "checkboxes": {},
    "radio": None,  # Will pick first choice
    "combobox": None,
    "multiselect": [],
}


def default_for_field(field):
    """Generate a sensible default value for a field based on its type."""
    datatype = field.get("datatype", "text")
    raw_datatype = field.get("raw_datatype", datatype)
    choices = field.get("choices", [])

    # Boolean types (the API often returns datatype="boolean" with inputtype="yesnowide")
    if raw_datatype == "boolean" or datatype == "boolean":
        return True

    # For choice-based fields, pick the first option
    if choices and datatype in ("radio", "combobox", None, "text"):
        if isinstance(choices[0], dict):
            # Format: [{"label": "...", "value": "..."}]
            return choices[0].get("value", choices[0].get("label"))
        elif isinstance(choices[0], list):
            # Format: [["value", "label"]]
            return choices[0][0]
        else:
            return choices[0]

    if datatype == "checkboxes":
        # For checkboxes, select the first option if available
        # The bracket notation expansion in the main loop will handle
        # converting this dict to individual key assignments
        result = {}
        if choices:
            if isinstance(choices[0], dict):
                key = choices[0].get("value", choices[0].get("label", "0"))
                result[key] = True
            elif isinstance(choices[0], list):
                result[choices[0][0]] = True
        return result

    return TYPE_DEFAULTS.get(datatype, "Test")


def extract_field_info(question):
    """Extract field variable names and metadata from a question response.

    The docassemble API returns fields with:
    - 'variable_name' (not 'variable') as the key for the variable name
    - 'datatype' for the field type (e.g. 'boolean', 'text', 'note')
    - 'inputtype' for how it's rendered (e.g. 'yesnowide', 'radio')
    - Fields with datatype 'note' are read-only text blocks (skip them)
    """
    fields = question.get("fields", [])
    result = []
    for field in fields:
        # The API uses 'variable_name', not 'variable'
        var_name = (
            field.get("variable_name")
            or field.get("variable")
            or field.get("var")
            or ""
        )

        datatype = field.get("datatype", "text")
        inputtype = field.get("inputtype", "")

        # Skip note/html fields — they're read-only, no variable to set
        if datatype in ("note", "html", "raw"):
            continue

        # Skip fields with no variable name
        if not var_name:
            continue

        # Use inputtype for more specific type resolution
        # (e.g., datatype="boolean" + inputtype="yesnowide" → treat as yesnowide)
        effective_type = inputtype if inputtype else datatype

        # Capture show_if conditions for conditional field filtering.
        # The API uses 'show_if_var' (variable name) and 'show_if_val' (value),
        # or 'show if' as a dict with 'variable' and 'is' keys.
        show_if_info = field.get("show if") or {}
        show_if_var = field.get("show_if_var") or ""
        show_if_val = field.get("show_if_val")
        if isinstance(show_if_info, dict):
            show_if_var = show_if_var or show_if_info.get("variable", "")
            show_if_val = show_if_val if show_if_val is not None else show_if_info.get("is")

        info = {
            "variable": var_name,
            "datatype": effective_type,
            "raw_datatype": datatype,
            "choices": field.get("choices", []),
            "required": field.get("required", True),
            "label": field.get("label", ""),
            "show_if": show_if_info,
            "show_if_var": show_if_var,
            "show_if_val": show_if_val,
        }
        result.append(info)
    return result


def get_question_variable_name(question):
    """Get the question_variable_name from the API response.

    This is the variable that docassemble is seeking to define. For
    continue_button_field screens, setting this to True advances the
    interview. For regular field screens, this is the first variable
    being sought (which will be set through the fields).

    Returns the variable name or None.
    """
    qvn = question.get("question_variable_name")
    if qvn:
        return qvn

    # Also check other possible key names
    for key in [
        "continue_button_field",
        "continueButtonField",
        "continue_field",
    ]:
        val = question.get(key)
        if val:
            return val

    # Fallback: check event_list (array of variable names this screen defines)
    event_list = question.get("event_list", [])
    if event_list and isinstance(event_list, list) and len(event_list) == 1:
        return event_list[0]

    return None


def resolve_generic_variable(field_var, question_var_name):
    """Resolve generic object variables (x, x[i]) to actual variable names.

    Docassemble uses 'x' as a placeholder in generic object questions.
    The actual object name can be inferred from question_variable_name.

    Examples:
        x.selected_types + income_list.selected_types -> income_list.selected_types
        x[i].source + income_list[0].source -> income_list[0].source
        x.there_are_any + motor_vehicles.there_are_any -> motor_vehicles.there_are_any
    """
    if not field_var or not question_var_name:
        return field_var

    # Check if the field uses generic 'x' placeholder
    if not (field_var.startswith("x.") or field_var.startswith("x[")):
        return field_var

    # Extract the object name from question_variable_name
    # e.g., "income_list.selected_types" -> "income_list"
    # e.g., "motor_vehicles.there_are_any" -> "motor_vehicles"
    # e.g., "income_list[0].source" -> "income_list"
    obj_name = question_var_name
    for sep in [".", "["]:
        if sep in obj_name:
            obj_name = obj_name.split(sep, 1)[0]
            break

    # Extract the index from question_variable_name if present
    # e.g., "income_list[0].source" -> index = "0"
    qvn_index = None
    idx_match = re.search(r'\[(\d+)\]', question_var_name)
    if idx_match:
        qvn_index = idx_match.group(1)

    # Replace 'x' with the actual object name
    if field_var.startswith("x."):
        return obj_name + field_var[1:]  # x.foo -> obj_name.foo
    elif field_var.startswith("x["):
        # Replace x[i] with obj_name[actual_index] if we know it
        if field_var.startswith("x[i]") and qvn_index is not None:
            return obj_name + "[" + qvn_index + "]" + field_var[4:]
        else:
            return obj_name + field_var[1:]  # x[...] -> obj_name[...]

    return field_var


def find_matching_test_vars(question, test_data):
    """Find variables from test_data that match the current question context.

    For screens where we can't directly map fields, check if any test_data
    keys correspond to known patterns for this screen.
    """
    q_id = question.get("id", "")
    q_text = str(question.get("question", "")).lower()

    # Direct screen ID match: if the test_data has a key matching the screen ID
    # (e.g., "al_intro_screen": true, "fs_intro": true)
    # Convert screen ID (with spaces) to possible variable names
    possible_var_names = set()
    if q_id:
        possible_var_names.add(q_id)
        # Convert "basic questions intro screen" -> "basic_questions_intro_screen"
        possible_var_names.add(q_id.replace(" ", "_"))
        # Convert "basic questions intro screen" -> "basic_questions_intro_screen"
        possible_var_names.add(q_id.replace("-", "_").replace(" ", "_"))

    # Check if any test data keys match these screen identifiers
    matches = {}
    for var_name in possible_var_names:
        if var_name in test_data:
            matches[var_name] = test_data[var_name]

    return matches


def is_error_screen(question):
    """Detect if the current screen is an error."""
    q_type = question.get("questionType", "")
    # The API uses 'questionText' and 'subquestionText' (not 'question'/'subquestion')
    q_text = str(question.get("questionText", question.get("question", ""))).lower()
    sub_text = str(question.get("subquestionText", question.get("subquestion", ""))).lower()

    # Explicit error states
    if q_type == "deadend":
        # Check if it's an actual error deadend vs. a normal end screen
        error_indicators = [
            "error", "traceback", "exception", "nameerror",
            "attributeerror", "typeerror", "keyerror", "indexerror",
        ]
        combined = q_text + " " + sub_text
        if any(kw in combined for kw in error_indicators):
            return True
        # A deadend without error keywords might be a normal terminal screen
        return False

    # Error keywords in question text
    error_keywords = [
        "there was an error",
        "an error occurred",
        "internal server error",
        "traceback",
        "exception",
        "nameerror",
        "attributeerror",
        "typeerror",
        "keyerror",
        "indexerror",
    ]
    combined = q_text + " " + sub_text
    return any(kw in combined for kw in error_keywords)


def is_terminal_screen(question):
    """Detect if the interview has reached a natural endpoint."""
    q_type = question.get("questionType", "")
    q_id = question.get("id", "")

    # Explicit terminal types
    if q_type in ("deadend", "restart", "exit"):
        return True

    # Event screens are terminal (like fs_download)
    if q_type == "event":
        return True

    # Known download/final screen IDs
    terminal_ids = {"fs_download", "a_divorce_agreement_download", "download"}
    if q_id in terminal_ids:
        return True

    # Check if event_list contains known terminal events
    event_list = question.get("event_list", [])
    terminal_events = {"fs_download", "a_divorce_agreement_download", "download"}
    if event_list and any(e in terminal_events for e in event_list):
        return True

    # A screen with no fields, no continue_button_field, and download-like content
    fields = extract_field_info(question)
    cbf = get_question_variable_name(question)
    if not fields and not cbf:
        sub = str(question.get("subquestionText", question.get("subquestion", ""))).lower()
        if any(w in sub for w in ["download", "your documents", "your forms", "all done"]):
            return True

    return False


def dump_question_debug(question, step):
    """Print a debug dump of the raw API response (sanitized for readability)."""
    # Keys to show in debug output
    interesting_keys = [
        "questionType", "id", "question", "subquestion",
        "continue_button_field", "continueButtonField",
        "continue_field", "event", "fields",
        "continue_button_label", "buttons",
        "question_variable_name", "variable_name",
    ]
    debug_data = {}
    for key in interesting_keys:
        if key in question:
            val = question[key]
            # Truncate long strings
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            debug_data[key] = val

    # Also show any keys we haven't seen before
    all_keys = set(question.keys())
    known_keys = set(interesting_keys) | {
        "css", "script", "help", "terms", "autoTerms",
        "title", "short_title", "decoration",
    }
    unknown_keys = all_keys - known_keys
    if unknown_keys:
        debug_data["_other_keys"] = sorted(unknown_keys)
        for k in sorted(unknown_keys):
            val = question[k]
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            elif isinstance(val, (list, dict)):
                val_str = json.dumps(val)
                if len(val_str) > 300:
                    val = val_str[:300] + "..."
            debug_data[k] = val

    print(f"    {CYAN}DEBUG Step {step}:{RESET}")
    print(f"    {json.dumps(debug_data, indent=2, default=str)}")


def run_scenario(client, scenario, verbose=False, debug=False):
    """Run a single test scenario through the interview.

    Returns (passed: bool, steps: int, message: str, details: list).
    """
    name = scenario.get("name", scenario.get("_file", "unknown"))
    interview = scenario["interview"]
    test_data = scenario.get("variables", {})
    max_steps = scenario.get("max_steps", 150)
    expect_screens = set(scenario.get("expect_screens", []))

    details = []
    seen_screens = set()
    # Track the previous screen to detect stuck loops
    prev_screen_id = None
    stuck_count = 0
    MAX_STUCK = 5  # Fail after seeing the same screen 5 times in a row
    # Track undefined variables we've tried to resolve (prevent infinite loops)
    undefined_var_attempts = {}
    # Track consumption of scenario-provided answer sequences.
    # Use "<var_name>__sequence" in scenario JSON to provide repeated answers
    # for the same variable across multiple screens (e.g., list gathers).
    sequence_counters = {}

    def lookup_test_value(*names):
        """Return (found, value) from scenario data, supporting __sequence keys."""
        for name in names:
            if not name:
                continue
            seq_key = f"{name}__sequence"
            seq_val = test_data.get(seq_key)
            if isinstance(seq_val, list):
                idx = sequence_counters.get(seq_key, 0)
                sequence_counters[seq_key] = idx + 1
                if not seq_val:
                    return True, None
                if idx < len(seq_val):
                    return True, seq_val[idx]
                return True, seq_val[-1]
            if name in test_data:
                return True, test_data[name]
        return False, None

    # Create session
    try:
        session_id, secret, i = client.new_session(interview)
    except Exception as e:
        return False, 0, f"Failed to create session: {e}", details

    try:
        for step in range(1, max_steps + 1):
            # Get current question
            try:
                question = client.get_question(session_id, secret, i)
            except Exception as e:
                details.append(f"Step {step}: API error getting question: {e}")
                return False, step, f"API error at step {step}: {e}", details

            q_type = question.get("questionType", "")
            q_id = question.get("id", "")
            q_text = question.get("questionText", question.get("question", ""))[:80]

            if q_id:
                seen_screens.add(q_id)

            # Debug mode: dump raw API response
            if debug and step <= 40:
                dump_question_debug(question, step)

            # Detect stuck loops (same screen 3+ times in a row)
            if q_id and q_id == prev_screen_id:
                stuck_count += 1
                if stuck_count >= MAX_STUCK:
                    details.append(
                        f"Step {step}: STUCK on screen '{q_id}' for {stuck_count} consecutive steps"
                    )
                    if debug:
                        dump_question_debug(question, step)
                    return False, step, f"Stuck on screen '{q_id}'", details
            else:
                stuck_count = 0
            prev_screen_id = q_id

            # Check for errors
            if is_error_screen(question):
                error_text = question.get("subquestion", question.get("question", ""))
                details.append(f"Step {step}: ERROR on screen '{q_id}': {error_text[:300]}")
                return False, step, f"Error screen at step {step} ({q_id})", details

            # Handle undefined_variable responses.
            # When docassemble can't resolve a variable (e.g., computed values
            # that depend on complex object internals like ALIncomeList.total()),
            # the API returns questionType="undefined_variable". We try to
            # resolve it by setting the variable directly from test_data.
            if q_type == "undefined_variable":
                undef_var = (
                    question.get("variable")
                    or question.get("question_variable_name")
                    or ""
                )
                if debug:
                    print(f"    {CYAN}undefined_variable: '{undef_var}'{RESET}")
                    for k in ("variable", "question_variable_name", "event_list",
                              "questionText", "subquestionText"):
                        if k in question:
                            print(f"    {CYAN}  {k}: {str(question[k])[:200]}{RESET}")

                if undef_var:
                    attempt_count = undefined_var_attempts.get(undef_var, 0)
                    if attempt_count >= 2:
                        details.append(
                            f"Step {step}: Cannot resolve undefined variable "
                            f"'{undef_var}' after {attempt_count} attempts"
                        )
                        return (
                            False, step,
                            f"Unresolvable undefined variable: {undef_var}",
                            details,
                        )
                    undefined_var_attempts[undef_var] = attempt_count + 1

                    found_undef, value = lookup_test_value(undef_var)
                    if found_undef:
                        if verbose or debug:
                            details.append(
                                f"Step {step}: Setting undefined var '{undef_var}' "
                                f"= {repr(value)[:80]} (from test_data)"
                            )
                        try:
                            client.set_variables(
                                session_id, secret, i, {undef_var: value}
                            )
                            continue
                        except Exception as e:
                            details.append(
                                f"Step {step}: Failed to set '{undef_var}': {e}"
                            )
                    else:
                        if verbose or debug:
                            details.append(
                                f"Step {step}: Undefined var '{undef_var}' not in "
                                f"test_data, setting to True"
                            )
                        try:
                            client.set_variables(
                                session_id, secret, i, {undef_var: True}
                            )
                            continue
                        except Exception as e:
                            details.append(
                                f"Step {step}: Failed to set '{undef_var}': {e}"
                            )
                else:
                    details.append(
                        f"Step {step}: undefined_variable with no variable name"
                    )
                    if debug:
                        dump_question_debug(question, step)

            # Check for natural end
            if is_terminal_screen(question):
                details.append(f"Step {step}: Reached terminal screen '{q_id}'")

                # Verify expected screens were visited
                if expect_screens:
                    missing = expect_screens - seen_screens
                    if missing:
                        details.append(f"  WARNING: Expected screens not seen: {missing}")
                        return False, step, f"Missing expected screens: {missing}", details

                return True, step, "Completed successfully", details

            # ── Determine what to send to advance ──

            # Get the question_variable_name (the variable docassemble is seeking)
            qvn = get_question_variable_name(question)

            # For "settrue" question type, set the continue_button_field to True.
            # Also handle any additional fields on the screen.
            if q_type == "settrue":
                variables = {}
                extra_fields = extract_field_info(question)
                has_cbf_field = False
                for field in extra_fields:
                    vn = field["variable"]
                    resolved = resolve_generic_variable(vn, qvn)
                    is_generic = vn.startswith("x.") or vn.startswith("x[")
                    send_var = vn if is_generic else resolved
                    found_value, val = lookup_test_value(resolved, vn)
                    if found_value:
                        variables[send_var] = val
                    else:
                        variables[send_var] = True
                    if resolved == qvn or vn == qvn:
                        has_cbf_field = True
                # Ensure the qvn is set even if not in fields
                if qvn and not has_cbf_field:
                    found_qvn, qvn_val = lookup_test_value(qvn)
                    if found_qvn:
                        variables[qvn] = qvn_val
                    else:
                        variables[qvn] = True

                if verbose:
                    details.append(
                        f"Step {step}: Screen '{q_id}' (settrue) — set {list(variables.keys())}"
                    )
                try:
                    resp = client.set_variables(session_id, secret, i, variables)
                    resp_type = resp.get("questionType", "")
                    if debug:
                        next_id = resp.get("id", "?")
                        print(f"    {CYAN}settrue response: next={next_id}, type={resp_type}{RESET}")

                    # Handle undefined_variable in settrue response.
                    # After setting a continue_button_field, docassemble may
                    # try to compute the next variable and fail. We resolve it
                    # here so the next get_question() can proceed.
                    undef_resolve_count = 0
                    while resp_type == "undefined_variable" and undef_resolve_count < 5:
                        undef_var = (
                            resp.get("variable")
                            or resp.get("question_variable_name")
                            or ""
                        )
                        if debug:
                            print(f"    {CYAN}  resolving undefined: '{undef_var}'{RESET}")
                        if not undef_var:
                            break
                        attempt_count = undefined_var_attempts.get(undef_var, 0)
                        if attempt_count >= 2:
                            details.append(
                                f"Step {step}: Cannot resolve '{undef_var}' "
                                f"after settrue (tried {attempt_count} times)"
                            )
                            break
                        undefined_var_attempts[undef_var] = attempt_count + 1

                        found_undef, val = lookup_test_value(undef_var)
                        if not found_undef:
                            val = True
                        if verbose or debug:
                            details.append(
                                f"Step {step}: Setting undefined '{undef_var}' "
                                f"= {repr(val)[:80]} (post-settrue)"
                            )
                        try:
                            resp = client.set_variables(
                                session_id, secret, i, {undef_var: val}
                            )
                            resp_type = resp.get("questionType", "")
                            undef_resolve_count += 1
                        except Exception as e2:
                            details.append(
                                f"Step {step}: Failed resolving '{undef_var}': {e2}"
                            )
                            break
                except Exception as e:
                    details.append(f"Step {step}: Error on settrue: {e}")
                    return False, step, f"Error at step {step}: {e}", details
                continue

            # Extract fields from the response
            fields = extract_field_info(question)

            # Build the variables to send
            variables = {}
            unknown_fields = []
            checkbox_vars_expanded = set()  # Track checkbox fields expanded to bracket notation

            # Resolve and set field values.
            # IMPORTANT: For generic object fields (x.foo, x[i].bar), we:
            #   - RESOLVE the name to look up values in test_data
            #   - USE THE ORIGINAL x-notation when sending to the API
            # Docassemble's API resolves 'x' internally in the question context.
            # Sending resolved names (e.g., income_list.selected_types) can fail
            # because the attribute may not exist as a Python object yet.
            for field in fields:
                raw_var = field["variable"]
                if not raw_var:
                    continue

                # Resolve generic 'x' variables to actual names for test_data lookup
                resolved_var = resolve_generic_variable(raw_var, qvn)

                # Determine which name to use for sending to the API:
                # - Generic fields (x.foo): use original raw_var (x.foo)
                # - Non-generic fields: use resolved (same as raw_var)
                is_generic = raw_var.startswith("x.") or raw_var.startswith("x[")
                send_var = raw_var if is_generic else resolved_var

                # Look up value: try resolved name first, then raw name
                found_value, value = lookup_test_value(
                    resolved_var, raw_var if raw_var != resolved_var else None
                )
                if found_value:
                    pass
                else:
                    # Auto-generate a value based on field type
                    value = default_for_field(field)
                    unknown_fields.append(resolved_var)

                # Checkbox fields (DADict): send as a serialized DADict object.
                # Individual bracket assignment fails because the DADict
                # attribute doesn't exist yet. Instead, send the complete
                # object with _class metadata so docassemble initializes it.
                raw_dt = field.get("raw_datatype", field.get("datatype", ""))
                if raw_dt == "checkboxes" and isinstance(value, dict):
                    # Build the complete checkbox dict for ALL available choices
                    elements = {}
                    choices = field.get("choices", [])
                    for choice in choices:
                        if isinstance(choice, dict):
                            key_match = re.search(r"\['(\w+)'\]",
                                                  choice.get("variable_name", ""))
                            if key_match:
                                cb_key = key_match.group(1)
                                elements[cb_key] = value.get(cb_key, False)
                    # If no structured choices, use the test data dict directly
                    if not elements:
                        elements = value

                    # Send as a serialized DADict object with _class metadata
                    variables[send_var] = {
                        "_class": "docassemble.base.util.DADict",
                        "instanceName": resolved_var,
                        "elements": elements,
                        "auto_gather": False,
                        "gathered": True,
                    }
                    checkbox_vars_expanded.add(resolved_var)
                else:
                    variables[send_var] = value

            # Filter out conditional fields whose show_if condition is not met.
            # When a field has show_if_var pointing to another field on the same
            # screen, and that field's value would hide this one, don't send it.
            # Sending hidden conditional fields causes 400 errors.
            fields_to_remove = set()
            for field in fields:
                sif_var = field.get("show_if_var", "")
                sif_val = field.get("show_if_val")
                if not sif_var:
                    continue
                raw_var = field["variable"]
                resolved_var = resolve_generic_variable(raw_var, qvn)
                is_generic = raw_var.startswith("x.") or raw_var.startswith("x[")
                send_var = raw_var if is_generic else resolved_var

                # Look up the controlling variable's value
                ctrl_val = variables.get(sif_var)
                if ctrl_val is None:
                    # Try resolved form
                    ctrl_val = variables.get(
                        resolve_generic_variable(sif_var, qvn)
                    )
                if ctrl_val is None:
                    continue  # Controller not in our variables, keep the field

                # Determine if the field should be visible
                if sif_val is not None:
                    # show if: {variable: X, is: Y} — visible when ctrl == Y
                    visible = str(ctrl_val).lower() == str(sif_val).lower()
                else:
                    # show if: X — visible when X is truthy
                    visible = bool(ctrl_val)

                if not visible and send_var in variables:
                    fields_to_remove.add(send_var)
                    if verbose or debug:
                        details.append(
                            f"  Hiding '{resolved_var}' (show_if {sif_var}={ctrl_val})"
                        )

            for var_to_remove in fields_to_remove:
                variables.pop(var_to_remove, None)

            # If question_variable_name is set and NOT already covered by
            # a field (i.e., it's a continue_button_field, not just the
            # first sought variable), add it.
            # qvn is the RESOLVED variable name (e.g., income_list.selected_types).
            # Check both resolved names and raw x-notation names.
            if qvn and qvn not in variables and qvn not in checkbox_vars_expanded:
                # For screens with fields, qvn is often the same as the
                # first field — only add if it's truly separate
                if not fields:
                    # No fields: this is a pure continue screen
                    found_qvn, qvn_val = lookup_test_value(qvn)
                    if found_qvn:
                        variables[qvn] = qvn_val
                    else:
                        variables[qvn] = True
                else:
                    # Has fields: check if qvn matches any field's resolved name
                    # Also check raw variable names (x-notation)
                    field_resolved = {resolve_generic_variable(f["variable"], qvn) for f in fields if f["variable"]}
                    field_raw = {f["variable"] for f in fields if f["variable"]}
                    all_field_vars = field_resolved | field_raw
                    if qvn not in all_field_vars and qvn not in checkbox_vars_expanded:
                        # qvn is separate (true continue_button_field)
                        found_qvn, qvn_val = lookup_test_value(qvn)
                        if found_qvn:
                            variables[qvn] = qvn_val
                        else:
                            variables[qvn] = True

            # If we still have nothing to send, try screen-ID fallbacks
            if not variables:
                screen_vars = find_matching_test_vars(question, test_data)
                if screen_vars:
                    variables = screen_vars

            if not variables and q_id:
                snake_id = q_id.replace(" ", "_").replace("-", "_")
                found_snake, snake_val = lookup_test_value(snake_id)
                if found_snake:
                    variables[snake_id] = snake_val
                else:
                    variables[snake_id] = True

            if verbose:
                field_summary = ", ".join(
                    resolve_generic_variable(f["variable"], qvn)
                    for f in fields if f["variable"]
                )
                details.append(
                    f"Step {step}: Screen '{q_id}' — fields: [{field_summary}]"
                )
                if qvn:
                    details.append(f"  question_variable_name: {qvn}")
                if unknown_fields:
                    details.append(f"  Auto-filled: {unknown_fields}")
                if not fields and not qvn:
                    details.append(f"  No fields/QVN detected, sending: {list(variables.keys())}")

            # Set variables and advance
            try:
                resp = client.set_variables(session_id, secret, i, variables)
                # Handle undefined_variable chain after field submission
                resp_type = resp.get("questionType", "")
                undef_resolve_count = 0
                while resp_type == "undefined_variable" and undef_resolve_count < 5:
                    undef_var = (
                        resp.get("variable")
                        or resp.get("question_variable_name")
                        or ""
                    )
                    if debug:
                        print(
                            f"    {CYAN}post-fields undefined: '{undef_var}'{RESET}"
                        )
                    if not undef_var:
                        break
                    attempt_count = undefined_var_attempts.get(undef_var, 0)
                    if attempt_count >= 2:
                        break
                    undefined_var_attempts[undef_var] = attempt_count + 1
                    found_undef, val = lookup_test_value(undef_var)
                    if not found_undef:
                        val = True
                    if verbose or debug:
                        details.append(
                            f"Step {step}: Setting undefined '{undef_var}' "
                            f"= {repr(val)[:80]} (post-fields)"
                        )
                    try:
                        resp = client.set_variables(
                            session_id, secret, i, {undef_var: val}
                        )
                        resp_type = resp.get("questionType", "")
                        undef_resolve_count += 1
                    except Exception as e2:
                        details.append(
                            f"Step {step}: Failed resolving '{undef_var}': {e2}"
                        )
                        break
            except requests.HTTPError as e:
                resp_text = ""
                if hasattr(e, "response") and e.response is not None:
                    try:
                        resp_text = e.response.text[:1000]
                    except Exception:
                        pass
                details.append(
                    f"Step {step}: HTTP error setting variables on '{q_id}': {e}"
                )
                details.append(f"  Variables: {json.dumps(variables, indent=2)[:500]}")
                if resp_text:
                    details.append(f"  Response: {resp_text}")
                # If we sent the snake_id variable and it failed, try empty
                if not fields and not qvn:
                    try:
                        client.set_variables(session_id, secret, i, {})
                        continue
                    except Exception:
                        pass
                return False, step, f"HTTP error at step {step} ({q_id})", details
            except Exception as e:
                details.append(f"Step {step}: Error: {e}")
                return False, step, f"Error at step {step}: {e}", details

        # Exceeded max steps
        return False, max_steps, f"Did not complete within {max_steps} steps", details

    finally:
        # Clean up session
        client.delete_session(session_id, secret, i)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generic API-driven interview test runner for docassemble"
    )
    parser.add_argument(
        "--scenario", help="Run only scenarios matching this name"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available scenarios and exit"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show every step"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Dump raw API JSON responses (first 10 steps per scenario)"
    )
    parser.add_argument(
        "--server", help="Override server URL from .env"
    )
    parser.add_argument(
        "--api-key", help="Override API key from .env"
    )
    args = parser.parse_args()

    # Load scenarios
    scenarios = load_scenarios(args.scenario)

    if args.list:
        if not scenarios:
            print(f"No scenarios found in {SCENARIOS_DIR}")
            print(f"Create JSON files there to define test scenarios.")
            sys.exit(0)

        print(f"\n{BOLD}Available test scenarios:{RESET}")
        print(f"{'─' * 70}")
        for s in scenarios:
            name = s.get("name", s["_file"])
            desc = s.get("description", "")
            interview = s.get("interview", "?")
            nvars = len(s.get("variables", {}))
            print(f"  {CYAN}{s['_file']}{RESET}")
            print(f"    Name: {name}")
            print(f"    Interview: {interview}")
            print(f"    Variables: {nvars}")
            if desc:
                print(f"    Description: {desc}")
            print()
        sys.exit(0)

    if not scenarios:
        print(f"{RED}No test scenarios found in {SCENARIOS_DIR}{RESET}")
        print(f"\nCreate JSON scenario files to define tests.")
        print(f"See the existing files for format examples.")
        sys.exit(1)

    # Load config
    server, api_key = load_env()
    if args.server:
        server = args.server
    if args.api_key:
        api_key = args.api_key

    # Check server
    client = DocassembleClient(server, api_key)
    if not server or not api_key:
        print(f"{RED}Server URL or API key not configured.{RESET}")
        sys.exit(1)

    if not client.health_check():
        print(f"{RED}Cannot reach docassemble server at {server}{RESET}")
        print(f"  Verify the server is running and the URL is correct.")
        sys.exit(1)

    # Run scenarios
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  Docassemble Interview Tests{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"  Server: {server}")
    print(f"  Scenarios: {len(scenarios)}")

    results = []
    total_start = time.time()

    for scenario in scenarios:
        name = scenario.get("name", scenario["_file"])
        print(f"\n{'─' * 70}")
        print(f"  {BOLD}{name}{RESET}")
        print(f"  {DIM}{scenario.get('description', '')}{RESET}")

        start = time.time()
        passed, steps, message, details = run_scenario(
            client, scenario, verbose=args.verbose, debug=args.debug
        )
        elapsed = time.time() - start

        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status} — {steps} steps, {elapsed:.1f}s — {message}")

        if args.verbose and details:
            for d in details:
                print(f"    {DIM}{d}{RESET}")

        if not passed and details:
            # Always show failure details
            for d in details[-5:]:  # Last 5 details
                print(f"    {d}")

        results.append((name, passed, steps, elapsed, message))

    # Summary
    total_time = time.time() - total_start
    passed_count = sum(1 for _, p, _, _, _ in results if p)
    failed_count = sum(1 for _, p, _, _, _ in results if not p)

    print(f"\n{'=' * 70}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{'=' * 70}")
    for name, passed, steps, elapsed, message in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name} ({steps} steps, {elapsed:.1f}s)")

    print(f"\n  Total: {len(results)} scenarios, "
          f"{GREEN}{passed_count} passed{RESET}", end="")
    if failed_count:
        print(f", {RED}{failed_count} failed{RESET}", end="")
    print(f"  ({total_time:.1f}s)")

    if failed_count:
        print(f"\n{RED}Some scenarios failed. See details above.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All scenarios passed!{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
