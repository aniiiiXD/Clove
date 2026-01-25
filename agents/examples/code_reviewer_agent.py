#!/usr/bin/env python3
"""
Code Reviewer Agent

A practical example agent that reviews Python files for common issues.
Demonstrates real-world use of Clove's capabilities:
- File reading (SYS_READ)
- LLM queries (SYS_THINK)
- Shell execution (SYS_EXEC)

Usage:
    python agents/examples/code_reviewer_agent.py <file_or_directory>

Example:
    python agents/examples/code_reviewer_agent.py agents/python_sdk/
"""

import sys
import json
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python_sdk"))
from clove_sdk import CloveClient


REVIEW_PROMPT = """Review this Python code for:
1. Security issues (SQL injection, command injection, hardcoded secrets)
2. Performance problems (N+1 queries, unnecessary loops)
3. Code style issues (naming, complexity)
4. Potential bugs (type errors, unhandled exceptions)

Be concise. List issues as bullet points. If the code is good, say so briefly.

Code:
```python
{code}
```"""


def review_file(client: CloveClient, filepath: str) -> dict:
    """Review a single Python file."""
    print(f"\n📄 Reviewing: {filepath}")

    # Read the file
    try:
        content = client.read(filepath)
    except Exception as e:
        return {"file": filepath, "error": f"Cannot read: {e}"}

    # Skip if too large
    if len(content) > 10000:
        return {"file": filepath, "error": "File too large (>10KB), skipping"}

    # Skip if empty
    if not content.strip():
        return {"file": filepath, "error": "Empty file"}

    # Ask LLM to review
    try:
        result = client.think(REVIEW_PROMPT.format(code=content))
        review = result.get('content', 'No response')
    except Exception as e:
        return {"file": filepath, "error": f"LLM error: {e}"}

    return {
        "file": filepath,
        "review": review,
        "lines": len(content.split('\n'))
    }


def find_python_files(client: CloveClient, path: str) -> list:
    """Find all Python files in a directory."""
    result = client.exec(f"find {path} -name '*.py' -type f 2>/dev/null | head -20")

    if result['exit_code'] != 0:
        return []

    files = [f.strip() for f in result['stdout'].strip().split('\n') if f.strip()]
    return files


def main():
    if len(sys.argv) < 2:
        print("Usage: python code_reviewer_agent.py <file_or_directory>")
        print("Example: python code_reviewer_agent.py ./src/")
        return 1

    target = sys.argv[1]

    print("╔════════════════════════════════════════════════════════════╗")
    print("║              CLOVE CODE REVIEWER AGENT                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    with CloveClient() as client:
        client.register("code-reviewer")

        # Determine if target is file or directory
        check = client.exec(f"test -f {target} && echo file || echo dir")
        is_file = check['stdout'].strip() == 'file'

        if is_file:
            files = [target]
        else:
            print(f"🔍 Scanning directory: {target}")
            files = find_python_files(client, target)
            print(f"   Found {len(files)} Python files")

        if not files:
            print("❌ No Python files found")
            return 1

        # Review each file
        reviews = []
        for filepath in files:
            review = review_file(client, filepath)
            reviews.append(review)

            if 'review' in review:
                print(f"\n{'─' * 50}")
                print(review['review'][:500])
                if len(review['review']) > 500:
                    print("... (truncated)")

        # Summary
        print()
        print("═" * 60)
        print("SUMMARY")
        print("═" * 60)
        print(f"Files reviewed: {len(reviews)}")

        errors = [r for r in reviews if 'error' in r]
        if errors:
            print(f"Errors: {len(errors)}")
            for e in errors:
                print(f"  - {e['file']}: {e['error']}")

        successful = [r for r in reviews if 'review' in r]
        total_lines = sum(r.get('lines', 0) for r in successful)
        print(f"Total lines reviewed: {total_lines}")

    print()
    print("✅ Review complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
