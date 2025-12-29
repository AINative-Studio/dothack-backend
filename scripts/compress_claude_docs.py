#!/usr/bin/env python3
"""
LLM-Powered Documentation Compression Script

Compresses .claude/*.md files to reduce token consumption in LLM context.
Uses OpenAI GPT-4o-mini for intelligent compression while preserving critical info.

Usage:
    python scripts/compress_claude_docs.py --target-ratio 0.3
    python scripts/compress_claude_docs.py --file .claude/RULES.MD --ratio 0.4
    python scripts/compress_claude_docs.py --all
"""

import os
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from openai import OpenAI


class DocCompressor:
    """Intelligent documentation compressor using LLM"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.compression_stats: List[Dict] = []

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars)"""
        return len(text) // 4

    def compress_document(
        self,
        content: str,
        target_ratio: float = 0.3,
        preserve_critical: bool = True
    ) -> Tuple[str, Dict]:
        """
        Compress markdown document to target_ratio of original tokens

        Args:
            content: Original document content
            target_ratio: Target size as ratio of original (0.3 = 70% reduction)
            preserve_critical: Keep all critical info (rules, commands, etc.)

        Returns:
            (compressed_content, stats_dict)
        """
        original_tokens = self.estimate_tokens(content)
        target_tokens = int(original_tokens * target_ratio)

        compression_prompt = f"""You are an expert technical writer specializing in ultra-dense documentation.

TASK: Compress this markdown to ~{target_tokens} tokens ({int(target_ratio*100)}% of original).

PRESERVE:
- ALL rules, requirements, and constraints
- File paths and code references
- Critical commands and workflows
- Error messages and warnings
- Technical specifications

REMOVE/CONDENSE:
- Verbose explanations
- Redundant examples
- Excessive formatting (emoji, decorative headers)
- Long descriptions (use telegraphic style)
- Whitespace and redundant sections

STYLE:
- Use bullet points over paragraphs
- Abbreviate common terms (e.g., "config" vs "configuration")
- Use tables for structured data
- Remove marketing/sales language
- Keep technical accuracy 100%

ORIGINAL DOCUMENT:
{content}

Return ONLY the compressed markdown. No preamble."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": compression_prompt}],
                temperature=0.3,  # Lower temp for consistency
                max_tokens=target_tokens + 500  # Slight buffer
            )

            compressed = response.choices[0].message.content
            compressed_tokens = self.estimate_tokens(compressed)

            stats = {
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "target_tokens": target_tokens,
                "actual_ratio": compressed_tokens / original_tokens if original_tokens > 0 else 0,
                "target_ratio": target_ratio,
                "reduction_pct": (1 - compressed_tokens / original_tokens) * 100 if original_tokens > 0 else 0,
                "original_chars": len(content),
                "compressed_chars": len(compressed),
            }

            return compressed, stats

        except Exception as e:
            print(f"Error during compression: {e}")
            return content, {"error": str(e)}

    def compress_file(
        self,
        input_path: Path,
        output_path: Path = None,
        target_ratio: float = 0.3
    ) -> Dict:
        """Compress a single markdown file"""

        if not input_path.exists():
            return {"error": f"File not found: {input_path}"}

        # Default output to compressed/ subdirectory
        if output_path is None:
            output_path = input_path.parent / "compressed" / input_path.name

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\nCompressing: {input_path.name}")
        print(f"Target ratio: {target_ratio*100:.0f}% ({100-target_ratio*100:.0f}% reduction)")

        # Read original
        content = input_path.read_text(encoding="utf-8")

        # Compress
        compressed, stats = self.compress_document(content, target_ratio)

        if "error" in stats:
            print(f"  ❌ Error: {stats['error']}")
            return stats

        # Write compressed version
        output_path.write_text(compressed, encoding="utf-8")

        # Print stats
        print(f"  ✓ Original: {stats['original_tokens']:,} tokens ({stats['original_chars']:,} chars)")
        print(f"  ✓ Compressed: {stats['compressed_tokens']:,} tokens ({stats['compressed_chars']:,} chars)")
        print(f"  ✓ Reduction: {stats['reduction_pct']:.1f}%")
        print(f"  ✓ Saved to: {output_path}")

        stats["input_file"] = str(input_path)
        stats["output_file"] = str(output_path)

        return stats

    def compress_directory(
        self,
        directory: Path,
        pattern: str = "*.md",
        target_ratio: float = 0.3,
        exclude: List[str] = None
    ) -> List[Dict]:
        """Compress all markdown files in directory"""

        exclude = exclude or ["compressed"]
        stats_list = []

        # Find all markdown files
        md_files = [
            f for f in directory.rglob(pattern)
            if not any(ex in str(f) for ex in exclude)
        ]

        print(f"\n{'='*70}")
        print(f"Compressing {len(md_files)} files in {directory}")
        print(f"Target compression ratio: {target_ratio*100:.0f}%")
        print(f"{'='*70}")

        for md_file in sorted(md_files):
            stats = self.compress_file(md_file, target_ratio=target_ratio)
            stats_list.append(stats)

        return stats_list

    def generate_report(self, stats_list: List[Dict], output_path: Path = None):
        """Generate compression report"""

        if not stats_list:
            print("No compression stats to report")
            return

        # Filter out errors
        valid_stats = [s for s in stats_list if "error" not in s]

        if not valid_stats:
            print("All compressions failed")
            return

        # Calculate totals
        total_original = sum(s["original_tokens"] for s in valid_stats)
        total_compressed = sum(s["compressed_tokens"] for s in valid_stats)
        total_reduction = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0

        # Generate report
        report = f"""# Documentation Compression Report

**Generated:** {Path(__file__).name}
**Files Processed:** {len(valid_stats)}
**Failed:** {len(stats_list) - len(valid_stats)}

## Summary

| Metric | Original | Compressed | Reduction |
|--------|----------|------------|-----------|
| **Total Tokens** | {total_original:,} | {total_compressed:,} | {total_reduction:.1f}% |
| **Avg per File** | {total_original//len(valid_stats):,} | {total_compressed//len(valid_stats):,} | - |

## Per-File Results

| File | Original | Compressed | Reduction |
|------|----------|------------|-----------|
"""

        for stat in sorted(valid_stats, key=lambda x: x["original_tokens"], reverse=True):
            filename = Path(stat["input_file"]).name
            report += f"| `{filename}` | {stat['original_tokens']:,} | {stat['compressed_tokens']:,} | {stat['reduction_pct']:.1f}% |\n"

        report += f"""
## Token Savings

- **Before:** {total_original:,} tokens total
- **After:** {total_compressed:,} tokens total
- **Saved:** {total_original - total_compressed:,} tokens ({total_reduction:.1f}%)

## Next Steps

1. Review compressed files in `.claude/compressed/`
2. Update your IDE/editor to use compressed versions for context
3. Keep originals for reference and editing
4. Re-run compression after major edits to originals

## Files Compressed

"""

        for stat in valid_stats:
            report += f"- `{Path(stat['input_file']).name}` → `{Path(stat['output_file']).relative_to(Path.cwd())}`\n"

        # Write report
        if output_path is None:
            output_path = Path(".claude/compressed/COMPRESSION_REPORT.md")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

        print(f"\n{'='*70}")
        print(f"COMPRESSION REPORT")
        print(f"{'='*70}")
        print(f"Total reduction: {total_reduction:.1f}%")
        print(f"Tokens saved: {total_original - total_compressed:,}")
        print(f"Report saved: {output_path}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compress .claude documentation files using LLM"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compress all .md files in .claude/"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Compress a specific file"
    )
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=0.3,
        help="Target compression ratio (default: 0.3 = 70%% reduction)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for compressed file (defaults to .claude/compressed/)"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".claude/compressed/COMPRESSION_REPORT.md"),
        help="Report output path"
    )

    args = parser.parse_args()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='sk-...'")
        return 1

    compressor = DocCompressor()

    if args.all:
        # Compress entire .claude directory
        stats = compressor.compress_directory(
            Path(".claude"),
            target_ratio=args.target_ratio,
            exclude=["compressed", "commands"]  # Skip compressed output and commands
        )
        compressor.generate_report(stats, args.report)

    elif args.file:
        # Compress single file
        stats = compressor.compress_file(
            args.file,
            output_path=args.output,
            target_ratio=args.target_ratio
        )

        if "error" not in stats:
            compressor.generate_report([stats], args.report)

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
