#!/usr/bin/env python3
"""Demo script for PromptGenerator - see outputs and tweak easily."""

from pathlib import Path
from stomper.ai.prompt_generator import PromptGenerator
from stomper.quality.base import QualityError


def create_demo_errors():
    """Create sample errors for demonstration."""
    return [
        QualityError(
            tool="ruff",
            file=Path("demo.py"),
            line=1,
            column=0,
            code="E501",
            message="Line too long (120 > 88 characters)",
            severity="error",
            auto_fixable=True
        ),
        QualityError(
            tool="ruff", 
            file=Path("demo.py"),
            line=5,
            column=0,
            code="F401",
            message="'os' imported but unused",
            severity="error",
            auto_fixable=True
        ),
        QualityError(
            tool="mypy",
            file=Path("demo.py"),
            line=10,
            column=0,
            code="missing-return-type",
            message="Function is missing a return type annotation",
            severity="error",
            auto_fixable=False
        )
    ]


def create_demo_code():
    """Create sample code context."""
    return '''import os
import sys
from typing import List

def process_data(items):
    """Process a list of items and return results."""
    results = []
    for item in items:
        if item is not None:
            results.append(item.upper())
    return results

def main():
    data = ["hello", "world", None, "python"]
    processed = process_data(data)
    print(f"Processed {len(processed)} items")

if __name__ == "__main__":
    main()
'''


def main():
    """Run the demo."""
    print("🧹 PromptGenerator Demo")
    print("=" * 50)
    
    # Create generator
    generator = PromptGenerator()
    
    # Create demo data
    errors = create_demo_errors()
    code_context = create_demo_code()
    
    print(f"📊 Input: {len(errors)} errors found")
    for error in errors:
        print(f"  - {error.tool}: {error.code} at line {error.line}")
    
    print(f"\n📝 Code context: {len(code_context.split())} words")
    print(f"Code preview: {code_context[:100]}...")
    
    print("\n" + "=" * 50)
    print("🤖 Generated Prompt:")
    print("=" * 50)
    
    # Generate prompt
    prompt = generator.generate_prompt(errors, code_context)
    
    print(prompt)
    
    print("\n" + "=" * 50)
    print(f"📏 Prompt stats:")
    print(f"  - Length: {len(prompt)} characters")
    print(f"  - Lines: {len(prompt.split(chr(10)))}")
    print(f"  - Words: {len(prompt.split())}")

    with open("prompt.md", "w") as f:
        f.write(prompt)


if __name__ == "__main__":
    main()
