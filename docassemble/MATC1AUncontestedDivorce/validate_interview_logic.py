#!/usr/bin/env python3
"""
Deep static analysis of docassemble interview logic.

Goes beyond YAML syntax validation to catch runtime-class bugs:
  1. Mako template variable extraction + cross-referencing
  2. Python code block AST parsing for syntax errors
  3. interview_order variable resolution (does every variable have a definition?)
  4. include file existence verification
  5. Orphan detection (defined but unreachable variables)
  6. Attachment field → variable tracing

Usage:
    python scripts/validate_interview_logic.py                   # Analyze all
    python scripts/validate_interview_logic.py --verbose          # Show all details
    python scripts/validate_interview_logic.py --file financial_statement.yml
"""

import ast
import re
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
QUESTIONS_DIR = PROJECT_ROOT / "docassemble" / "MATC1AUncontestedDivorce" / "data" / "questions"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Mako expression pattern: ${ ... }
MAKO_EXPR = re.compile(r'\$\{\s*(.+?)\s*\}', re.DOTALL)

# Variable name pattern (Python identifier, possibly with dots and brackets)
VAR_NAME = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\]|\[i\])*')

# docassemble built-in functions that are always available
DA_BUILTINS = {
    # Core docassemble functions
    "value", "defined", "showifdef", "set_progress", "nav", "currency",
    "comma_and_list", "word", "bold", "italic", "url_action", "action_arguments",
    "action_button_html", "get_config", "log", "force_ask", "force_gather",
    "reconsider", "need", "encode_name", "decode_name", "interview_url",
    "interview_url_action", "background_action", "background_response",
    "background_response_action", "background_error_action", "user_info",
    "user_logged_in", "user_has_privilege", "set_info", "get_info",
    "interface", "device", "language_from_browser", "set_language",
    "get_language", "prevent_going_back", "allow_cron", "incoming_email",
    "role_event", "set_parts", "send_email", "send_sms", "map_of",
    "include_docx_template", "pdf_concatenate", "zip_file",
    "overlay_pdf", "objects_from_file", "define", "undefine", "forget",
    "re_run_logic", "all_variables", "session_tags",
    # Python builtins
    "True", "False", "None", "len", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple", "range", "enumerate", "zip",
    "sorted", "reversed", "min", "max", "sum", "abs", "round",
    "isinstance", "hasattr", "getattr", "setattr", "type",
    "print", "format", "repr", "chr", "ord",
    # Common imports available in docassemble
    "DAObject", "DAList", "DADict", "DASet", "DAFile", "DAFileList",
    "DAFileCollection", "DAStaticFile", "DAEmail", "DATemplate",
    "Individual", "Person", "Name", "Address", "LatitudeLongitude",
    "Organization", "ALPeopleList", "ALIndividual", "ALAddress",
    "ALDocument", "ALDocumentBundle", "MACourt", "DAAddress",
    "ALIncomeList", "ALExpenseList", "ALIncome", "ALExpense",
    "ALAsset", "ALAssetList", "ALVehicle", "ALVehicleList",
    # Docassemble template functions
    "today", "format_date", "format_time", "format_datetime",
    "date_interval", "date_difference", "as_datetime",
    # Common Assembly Line functions
    "to_weekly", "cadence_to_times_per_year",
}

# Variables defined by docassemble itself or Assembly Line
DA_AUTO_VARS = {
    "i", "x", "j", "self",  # loop/generic variables
    "al_intro_screen", "al_nav_sections", "enable_al_nav_sections",
    "interview_short_title", "allowed_courts",
    "user_role", "user_ask_role",
    "al_user_bundle", "al_court_bundle",
}


class InterviewBlock:
    """Represents a single YAML block (--- separated) in a docassemble interview."""
    def __init__(self, data, source_file, block_index):
        self.data = data or {}
        self.source_file = source_file
        self.block_index = block_index

    @property
    def block_type(self):
        if not self.data:
            return "empty"
        if "question" in self.data:
            return "question"
        if "code" in self.data:
            return "code"
        if "objects" in self.data:
            return "objects"
        if "attachment" in self.data or "attachments" in self.data:
            return "attachment"
        if "template" in self.data and "content" in self.data:
            return "template"
        if "review" in self.data:
            return "review"
        if "table" in self.data:
            return "table"
        if "include" in self.data:
            return "include"
        if "metadata" in self.data:
            return "metadata"
        if "sections" in self.data:
            return "sections"
        if "modules" in self.data:
            return "modules"
        if "variable name" in self.data and "data" in self.data:
            return "data"
        if "initial" in self.data:
            return "initial_code"
        return "other"

    @property
    def block_id(self):
        return self.data.get("id", f"{self.source_file}:block_{self.block_index}")

    @property
    def sets_variables(self):
        """Variables this block can define/set."""
        result = set()
        # Explicit 'sets' key
        if "sets" in self.data:
            s = self.data["sets"]
            if isinstance(s, list):
                result.update(s)
            elif isinstance(s, str):
                result.add(s)
        # 'continue button field' sets a variable
        if "continue button field" in self.data:
            result.add(self.data["continue button field"])
        # 'event' key defines a variable (used for event-driven screens like downloads)
        if "event" in self.data:
            result.add(self.data["event"])
        # 'template' key defines a template variable
        if "template" in self.data and self.block_type == "template":
            result.add(self.data["template"])
        # 'table' key defines a table attribute
        if "table" in self.data:
            result.add(self.data["table"])
        # 'review' blocks with event define a review event variable
        if "review" in self.data and "event" in self.data:
            pass  # Already handled by event above
        # Fields in question blocks
        if "fields" in self.data and self.block_type == "question":
            for field in self.data["fields"]:
                if isinstance(field, dict):
                    for key, val in field.items():
                        if key not in ("note", "html", "help", "label", "show if",
                                       "hide if", "js show if", "js hide if",
                                       "disable if", "required", "datatype",
                                       "input type", "code", "choices",
                                       "default", "min", "max", "step",
                                       "maxlength", "minlength", "rows",
                                       "hint", "under", "css class", "field css class"):
                            if isinstance(val, str) and not val.startswith("$"):
                                result.add(val)
        # Variable name in data blocks
        if "variable name" in self.data and self.block_type == "data":
            result.add(self.data["variable name"])
        # Generic object blocks set indexed variables
        if "generic object" in self.data:
            # These are pattern-based, handled specially
            pass
        return result

    @property
    def fields_asked(self):
        """Field variable names this question block asks for."""
        result = []
        if "fields" in self.data and self.block_type == "question":
            for field in self.data["fields"]:
                if isinstance(field, dict):
                    for key, val in field.items():
                        if key not in ("note", "html", "help", "label", "show if",
                                       "hide if", "js show if", "js hide if",
                                       "disable if", "required", "datatype",
                                       "input type", "code", "choices",
                                       "default", "min", "max", "step",
                                       "maxlength", "minlength", "rows",
                                       "hint", "under", "css class", "field css class"):
                            if isinstance(val, str) and not val.startswith("$"):
                                result.append(val)
        return result


class InterviewAnalyzer:
    """Performs deep static analysis on docassemble interview YAML files."""

    def __init__(self, questions_dir):
        self.questions_dir = Path(questions_dir)
        self.blocks = []           # All InterviewBlock objects
        self.files_loaded = []     # Filenames loaded
        self.issues = []           # (severity, category, message, file, block_id)
        self.vars_defined = {}     # var_name -> defining block
        self.vars_referenced = defaultdict(set)  # var_name -> set of referencing locations
        self.code_blocks = []      # (code_string, block_id, file)
        self.includes = []         # List of include paths
        self.mako_expressions = [] # (expression, location)
        self.verbose = False

    def load_all_files(self, target_file=None):
        """Load and parse all YAML files."""
        if target_file:
            files = [self.questions_dir / target_file]
        else:
            files = sorted(self.questions_dir.glob("*.yml"))

        for yml_file in files:
            if yml_file.name.startswith("_") or yml_file.name.startswith("."):
                continue
            try:
                with open(yml_file, encoding="utf-8") as f:
                    docs = list(yaml.safe_load_all(f))

                for idx, doc in enumerate(docs):
                    if doc is not None:
                        block = InterviewBlock(doc, yml_file.name, idx)
                        self.blocks.append(block)

                self.files_loaded.append(yml_file.name)
            except yaml.YAMLError as e:
                self.issues.append(("ERROR", "yaml_parse", f"YAML parse error: {e}",
                                    yml_file.name, None))

    def analyze(self):
        """Run all analysis passes."""
        self._pass1_catalog_definitions()
        self._pass2_check_code_blocks()
        self._pass3_extract_mako_references()
        self._pass4_check_interview_order()
        self._pass5_check_includes()
        self._pass6_check_attachment_references()
        self._pass7_check_orphans()

    def _pass1_catalog_definitions(self):
        """Pass 1: Build a map of all variable definitions."""
        for block in self.blocks:
            for var in block.sets_variables:
                if var in self.vars_defined:
                    # Multiple definitions — might be intentional (different code paths)
                    existing = self.vars_defined[var]
                    if existing.source_file != block.source_file:
                        if self.verbose:
                            self.issues.append((
                                "INFO", "multi_def",
                                f"Variable '{var}' defined in both "
                                f"{existing.source_file} and {block.source_file}",
                                block.source_file, block.block_id
                            ))
                self.vars_defined[var] = block

            # Objects blocks define variables too
            if block.block_type == "objects":
                objs = block.data.get("objects", [])
                if isinstance(objs, list):
                    for obj_def in objs:
                        if isinstance(obj_def, dict):
                            for name in obj_def:
                                self.vars_defined[name] = block
                        elif isinstance(obj_def, str) and ":" in obj_def:
                            name = obj_def.split(":")[0].strip().lstrip("- ")
                            self.vars_defined[name] = block

            # Code blocks — parse assignments
            if block.block_type in ("code", "initial_code"):
                code_str = block.data.get("code", "")
                if code_str:
                    self.code_blocks.append((code_str, block.block_id, block.source_file))
                    try:
                        tree = ast.parse(code_str)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Assign, ast.AugAssign)):
                                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                                for target in targets:
                                    if isinstance(target, ast.Name):
                                        self.vars_defined[target.id] = block
                                    elif isinstance(target, ast.Subscript):
                                        if isinstance(target.value, ast.Name):
                                            # e.g. financial_form_type = "short"
                                            pass  # Already caught by sets_variables
                    except SyntaxError:
                        pass  # Caught in pass 2

    def _pass2_check_code_blocks(self):
        """Pass 2: Parse all code blocks with AST and check for syntax errors."""
        for code_str, block_id, source_file in self.code_blocks:
            # Check for Python syntax errors
            try:
                tree = ast.parse(code_str)
            except SyntaxError as e:
                self.issues.append((
                    "ERROR", "code_syntax",
                    f"Python syntax error in code block: {e.msg} (line {e.lineno})",
                    source_file, block_id
                ))
                continue

            # Check for common mistakes
            visitor = CodeAnalyzer()
            visitor.visit(tree)

            for issue_msg in visitor.issues:
                self.issues.append((
                    "WARNING", "code_quality",
                    issue_msg, source_file, block_id
                ))

            # Track referenced variables
            for ref in visitor.referenced:
                self.vars_referenced[ref].add(f"{source_file}:{block_id}")

    def _pass3_extract_mako_references(self):
        """Pass 3: Extract variable references from Mako ${ } expressions."""
        for block in self.blocks:
            self._scan_dict_for_mako(block.data, block.source_file, block.block_id)

    def _scan_dict_for_mako(self, obj, source_file, block_id):
        """Recursively scan a dict/list for Mako expressions."""
        if isinstance(obj, str):
            for match in MAKO_EXPR.finditer(obj):
                expr = match.group(1)
                self.mako_expressions.append((expr, source_file, block_id))
                # Extract variable names from the expression
                for var_match in VAR_NAME.finditer(expr):
                    var_name = var_match.group(0)
                    # Skip known function names and keywords
                    if var_name not in DA_BUILTINS and var_name not in (
                        "if", "else", "for", "in", "not", "and", "or",
                        "is", "None", "True", "False", "try", "except",
                    ):
                        self.vars_referenced[var_name].add(
                            f"mako:{source_file}:{block_id}"
                        )
        elif isinstance(obj, dict):
            for val in obj.values():
                self._scan_dict_for_mako(val, source_file, block_id)
        elif isinstance(obj, list):
            for item in obj:
                self._scan_dict_for_mako(item, source_file, block_id)

    def _pass4_check_interview_order(self):
        """Pass 4: Trace interview_order code blocks and verify variable resolution."""
        for code_str, block_id, source_file in self.code_blocks:
            if "interview_order" not in block_id and "interview_order" not in code_str[:100]:
                continue

            # This is an interview_order block — every bare name reference
            # is a variable that docassemble needs to resolve
            try:
                tree = ast.parse(code_str)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Name):
                    var_name = node.value.id
                    if var_name in ("True", "False", "None"):
                        continue
                    # Skip nav.set_section, set_progress calls
                    if var_name in DA_BUILTINS or var_name in DA_AUTO_VARS:
                        continue

                    # Check if this variable has a defining block
                    if var_name not in self.vars_defined:
                        # Could be defined by an included file — check common patterns
                        if not self._is_likely_external(var_name):
                            self.issues.append((
                                "ERROR", "missing_definition",
                                f"interview_order references '{var_name}' but no "
                                f"question or code block defines it",
                                source_file, block_id
                            ))
                        else:
                            if self.verbose:
                                self.issues.append((
                                    "INFO", "external_var",
                                    f"'{var_name}' likely defined by an included package",
                                    source_file, block_id
                                ))

                # Check attribute access like users[0].name.first
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Subscript):
                    # e.g. users[0].name.first — the root object 'users' should be defined
                    root = self._get_root_name(node.value)
                    if root and root not in self.vars_defined and root not in DA_BUILTINS:
                        if not self._is_likely_external(root):
                            self.issues.append((
                                "WARNING", "missing_root_object",
                                f"interview_order references '{root}' (via subscript) "
                                f"but no objects block defines it",
                                source_file, block_id
                            ))

    def _pass5_check_includes(self):
        """Pass 5: Verify included files exist (local files only)."""
        for block in self.blocks:
            if block.block_type != "include" or "include" not in block.data:
                continue
            includes = block.data["include"]
            if isinstance(includes, str):
                includes = [includes]
            for inc_path in includes:
                if ":" in inc_path:
                    # External package include (e.g., docassemble.AssemblyLine:assembly_line.yml)
                    # We can't verify these without the package installed
                    self.includes.append(("external", inc_path, block.source_file))
                    if self.verbose:
                        self.issues.append((
                            "INFO", "external_include",
                            f"External include: {inc_path}",
                            block.source_file, block.block_id
                        ))
                else:
                    # Local include — verify it exists
                    local_path = self.questions_dir / inc_path
                    if not local_path.exists():
                        self.issues.append((
                            "ERROR", "missing_include",
                            f"Included file not found: {inc_path}",
                            block.source_file, block.block_id
                        ))
                    else:
                        self.includes.append(("local", inc_path, block.source_file))

    def _pass6_check_attachment_references(self):
        """Pass 6: Check that attachment blocks reference valid PDF template files."""
        for block in self.blocks:
            if block.block_type != "attachment":
                continue

            att = block.data.get("attachment") or block.data.get("attachments")
            if not att:
                continue

            # Handle single attachment (dict) or list
            atts = [att] if isinstance(att, dict) else (att if isinstance(att, list) else [])
            if not atts and isinstance(att, dict):
                atts = [att]

            # For attachment blocks that are at the top level (not nested under "attachment:")
            if "pdf template file" in block.data:
                atts = [block.data]

            for att_item in atts:
                if not isinstance(att_item, dict):
                    continue
                pdf_file = att_item.get("pdf template file")
                if pdf_file:
                    # Check if the PDF exists in the templates directory
                    templates_dir = (PROJECT_ROOT / "docassemble" /
                                     "MATC1AUncontestedDivorce" / "data" / "templates")
                    static_dir = (PROJECT_ROOT / "docassemble" /
                                  "MATC1AUncontestedDivorce" / "data" / "static")
                    if not (templates_dir / pdf_file).exists() and not (static_dir / pdf_file).exists():
                        self.issues.append((
                            "ERROR", "missing_pdf_template",
                            f"PDF template file not found: {pdf_file}",
                            block.source_file, block.block_id
                        ))

                # Check Mako expressions in attachment field values
                fields = att_item.get("fields")
                if fields and isinstance(fields, dict):
                    for field_name, field_val in fields.items():
                        if isinstance(field_val, str):
                            for match in MAKO_EXPR.finditer(field_val):
                                expr = match.group(1)
                                for var_match in VAR_NAME.finditer(expr):
                                    var_name = var_match.group(0)
                                    if (var_name not in DA_BUILTINS and
                                        var_name not in ("if", "else", "not", "and", "or")):
                                        self.vars_referenced[var_name].add(
                                            f"attachment:{block.source_file}:{field_name}"
                                        )

    def _pass7_check_orphans(self):
        """Pass 7: Find variables defined but never referenced (potential dead code)."""
        if not self.verbose:
            return

        for var_name, block in self.vars_defined.items():
            if var_name in DA_AUTO_VARS:
                continue
            if var_name.startswith("_"):
                continue
            if var_name not in self.vars_referenced:
                self.issues.append((
                    "INFO", "orphan_definition",
                    f"Variable '{var_name}' is defined but never referenced "
                    f"(may be used by docassemble internally)",
                    block.source_file, block.block_id
                ))

    def _is_likely_external(self, var_name):
        """Check if a variable is likely defined by an external included package."""
        external_patterns = [
            "al_", "AL",  # Assembly Line
            "mac_", "mass",  # Massachusetts
        ]
        return any(var_name.startswith(p) or var_name.startswith(p.upper())
                    for p in external_patterns) or var_name in DA_AUTO_VARS

    def _get_root_name(self, node):
        """Get the root variable name from a subscript/attribute chain."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Subscript):
            return self._get_root_name(node.value)
        if isinstance(node, ast.Attribute):
            return self._get_root_name(node.value)
        return None

    def report(self):
        """Print analysis results."""
        errors = [i for i in self.issues if i[0] == "ERROR"]
        warnings = [i for i in self.issues if i[0] == "WARNING"]
        infos = [i for i in self.issues if i[0] == "INFO"]

        print(f"\n{BOLD}{'=' * 70}{RESET}")
        print(f"{BOLD}  Interview Logic Analysis Report{RESET}")
        print(f"{BOLD}{'=' * 70}{RESET}")

        # Summary stats
        question_blocks = sum(1 for b in self.blocks if b.block_type == "question")
        code_blocks_count = len(self.code_blocks)
        total_vars_defined = len(self.vars_defined)
        total_vars_referenced = len(self.vars_referenced)
        total_mako = len(self.mako_expressions)

        print(f"\n  {CYAN}Files analyzed:{RESET}    {len(self.files_loaded)}")
        print(f"  {CYAN}YAML blocks:{RESET}       {len(self.blocks)}")
        print(f"  {CYAN}Question screens:{RESET}   {question_blocks}")
        print(f"  {CYAN}Code blocks:{RESET}        {code_blocks_count}")
        print(f"  {CYAN}Variables defined:{RESET}   {total_vars_defined}")
        print(f"  {CYAN}Variables referenced:{RESET} {total_vars_referenced}")
        print(f"  {CYAN}Mako expressions:{RESET}   {total_mako}")
        print(f"  {CYAN}Include files:{RESET}      {len(self.includes)} "
              f"({sum(1 for t, _, _ in self.includes if t == 'local')} local, "
              f"{sum(1 for t, _, _ in self.includes if t == 'external')} external)")

        if errors:
            print(f"\n  {RED}{BOLD}ERRORS ({len(errors)}):{RESET}")
            for sev, cat, msg, file, bid in errors:
                print(f"    {RED}✗{RESET} [{cat}] {msg}")
                print(f"      {DIM}in {file}" + (f" ({bid})" if bid else "") + f"{RESET}")

        if warnings:
            print(f"\n  {YELLOW}{BOLD}WARNINGS ({len(warnings)}):{RESET}")
            for sev, cat, msg, file, bid in warnings:
                print(f"    {YELLOW}⚠{RESET} [{cat}] {msg}")
                print(f"      {DIM}in {file}" + (f" ({bid})" if bid else "") + f"{RESET}")

        if infos and self.verbose:
            print(f"\n  {CYAN}INFO ({len(infos)}):{RESET}")
            for sev, cat, msg, file, bid in infos:
                print(f"    {DIM}ℹ [{cat}] {msg}")
                print(f"      in {file}" + (f" ({bid})" if bid else "") + f"{RESET}")

        # Final verdict
        print(f"\n{'=' * 70}")
        if errors:
            print(f"  {RED}{BOLD}RESULT: {len(errors)} error(s), "
                  f"{len(warnings)} warning(s){RESET}")
        elif warnings:
            print(f"  {YELLOW}{BOLD}RESULT: 0 errors, "
                  f"{len(warnings)} warning(s){RESET}")
        else:
            print(f"  {GREEN}{BOLD}RESULT: No issues found{RESET}")
        print(f"{'=' * 70}\n")

        return errors


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor that checks for common code issues."""

    def __init__(self):
        self.issues = []
        self.assigned = set()
        self.referenced = set()
        self.in_function_def = False
        self.function_locals = set()

    def visit_FunctionDef(self, node):
        """Track function definitions and their local vars."""
        self.in_function_def = True
        self.function_locals = {arg.arg for arg in node.args.args}
        self.generic_visit(node)
        self.in_function_def = False
        self.function_locals = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.assigned.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            if node.id not in self.function_locals:
                self.referenced.add(node.id)
        self.generic_visit(node)

    def visit_Try(self, node):
        """Check for bare except clauses."""
        for handler in node.handlers:
            if handler.type is None:
                # Bare except — not necessarily an error in docassemble context
                # (used for undefined variable catching) but worth noting
                pass
        self.generic_visit(node)

    def visit_Call(self, node):
        """Track function calls."""
        if isinstance(node.func, ast.Name):
            self.referenced.add(node.func.id)
        self.generic_visit(node)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Deep static analysis of docassemble interview logic"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all details including INFO-level findings")
    parser.add_argument("--file", "-f", type=str, default=None,
                        help="Analyze a specific file only")
    args = parser.parse_args()

    print(f"\n{BOLD}=== Interview Logic Analysis ==={RESET}")
    print(f"Directory: {QUESTIONS_DIR}\n")

    analyzer = InterviewAnalyzer(QUESTIONS_DIR)
    analyzer.verbose = args.verbose
    analyzer.load_all_files(target_file=args.file)

    if not analyzer.files_loaded:
        print(f"{RED}No files found to analyze{RESET}")
        sys.exit(1)

    print(f"  Loaded {len(analyzer.files_loaded)} files, "
          f"{len(analyzer.blocks)} blocks")

    analyzer.analyze()
    errors = analyzer.report()

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
