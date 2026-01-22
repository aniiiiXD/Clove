#!/usr/bin/env python3
"""
Research Team Benchmark

Compares:
1. LangGraph version (StateGraph pattern)
2. Clove version (single process, kernel-mediated LLM)
3. Clove multi-process version (real agent isolation)

Both use the same Gemini model for fair comparison.
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'agents', 'python_sdk'))


def run_langgraph_benchmark(topic: str, iterations: int = 3) -> Dict:
    """Run LangGraph benchmark"""
    from langgraph_version import ResearchTeam

    results = []
    errors = 0

    print(f"\n  Running {iterations} iterations...")

    for i in range(iterations):
        try:
            team = ResearchTeam()
            result = team.run(topic, max_iterations=5)
            results.append({
                "elapsed_ms": result["elapsed_ms"],
                "iterations": result["iterations"],
                "notes_count": len(result["research_notes"]),
                "report_length": len(result["final_report"])
            })
            print(f"    Iteration {i+1}: {result['elapsed_ms']:.0f}ms")
        except Exception as e:
            print(f"    Iteration {i+1}: ERROR - {e}")
            errors += 1

    if not results:
        return {"error": "All iterations failed"}

    return {
        "framework": "langgraph",
        "iterations": len(results),
        "errors": errors,
        "mean_ms": sum(r["elapsed_ms"] for r in results) / len(results),
        "min_ms": min(r["elapsed_ms"] for r in results),
        "max_ms": max(r["elapsed_ms"] for r in results),
        "avg_workflow_iterations": sum(r["iterations"] for r in results) / len(results),
        "avg_notes": sum(r["notes_count"] for r in results) / len(results),
        "avg_report_length": sum(r["report_length"] for r in results) / len(results),
        "raw_results": results
    }


def run_clove_benchmark(topic: str, iterations: int = 3) -> Dict:
    """Run Clove single-process benchmark"""
    from clove_version import ResearchTeam

    results = []
    errors = 0

    print(f"\n  Running {iterations} iterations...")

    for i in range(iterations):
        try:
            with ResearchTeam() as team:
                result = team.run(topic, max_iterations=5)
                results.append({
                    "elapsed_ms": result["elapsed_ms"],
                    "iterations": result["iterations"],
                    "notes_count": len(result["research_notes"]),
                    "report_length": len(result["final_report"])
                })
                print(f"    Iteration {i+1}: {result['elapsed_ms']:.0f}ms")
        except Exception as e:
            print(f"    Iteration {i+1}: ERROR - {e}")
            errors += 1

    if not results:
        return {"error": "All iterations failed"}

    return {
        "framework": "clove",
        "iterations": len(results),
        "errors": errors,
        "mean_ms": sum(r["elapsed_ms"] for r in results) / len(results),
        "min_ms": min(r["elapsed_ms"] for r in results),
        "max_ms": max(r["elapsed_ms"] for r in results),
        "avg_workflow_iterations": sum(r["iterations"] for r in results) / len(results),
        "avg_notes": sum(r["notes_count"] for r in results) / len(results),
        "avg_report_length": sum(r["report_length"] for r in results) / len(results),
        "raw_results": results
    }


def run_clove_multiprocess_benchmark(topic: str, iterations: int = 3) -> Dict:
    """Run Clove multi-process benchmark"""
    from clove_multiprocess import MultiProcessResearchTeam

    results = []
    errors = 0

    print(f"\n  Running {iterations} iterations...")

    for i in range(iterations):
        try:
            with MultiProcessResearchTeam() as team:
                result = team.run(topic, max_iterations=5)
                results.append({
                    "elapsed_ms": result["elapsed_ms"],
                    "iterations": result["iterations"],
                    "notes_count": len(result["research_notes"]),
                    "report_length": len(result["final_report"]),
                    "agents_spawned": result["agents_spawned"]
                })
                print(f"    Iteration {i+1}: {result['elapsed_ms']:.0f}ms (spawned {result['agents_spawned']} agents)")
        except Exception as e:
            print(f"    Iteration {i+1}: ERROR - {e}")
            errors += 1

    if not results:
        return {"error": "All iterations failed"}

    return {
        "framework": "clove_multiprocess",
        "iterations": len(results),
        "errors": errors,
        "mean_ms": sum(r["elapsed_ms"] for r in results) / len(results),
        "min_ms": min(r["elapsed_ms"] for r in results),
        "max_ms": max(r["elapsed_ms"] for r in results),
        "avg_workflow_iterations": sum(r["iterations"] for r in results) / len(results),
        "avg_notes": sum(r["notes_count"] for r in results) / len(results),
        "avg_report_length": sum(r["report_length"] for r in results) / len(results),
        "avg_agents": sum(r.get("agents_spawned", 0) for r in results) / len(results),
        "raw_results": results
    }


def print_comparison(results: List[Dict]):
    """Print comparison table"""

    print("\n" + "=" * 80)
    print("  BENCHMARK COMPARISON: Multi-Agent Research Team")
    print("=" * 80)

    # Header
    print(f"\n{'Framework':<20} {'Mean (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Errors':<8}")
    print("-" * 80)

    # Results
    for r in results:
        if "error" in r:
            print(f"{r.get('framework', 'unknown'):<20} {'FAILED':<12}")
        else:
            print(f"{r['framework']:<20} {r['mean_ms']:<12.0f} {r['min_ms']:<12.0f} {r['max_ms']:<12.0f} {r['errors']:<8}")

    print("-" * 80)

    # Find winner
    valid_results = [r for r in results if "error" not in r]
    if len(valid_results) >= 2:
        winner = min(valid_results, key=lambda x: x["mean_ms"])
        print(f"\nWinner: {winner['framework']} ({winner['mean_ms']:.0f}ms mean)")

        # Calculate speedup
        for r in valid_results:
            if r != winner:
                speedup = r["mean_ms"] / winner["mean_ms"]
                print(f"  vs {r['framework']}: {speedup:.2f}x faster")


def save_results(results: List[Dict], output_dir: str):
    """Save results to JSON"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"research_team_benchmark_{timestamp}.json")

    with open(filepath, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "results": results
        }, f, indent=2)

    print(f"\nResults saved to: {filepath}")


def main():
    """Run all benchmarks"""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Research Team implementations")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per framework")
    parser.add_argument("--topic", type=str, default="The benefits and challenges of microservices architecture")
    parser.add_argument("--langgraph-only", action="store_true", help="Only run LangGraph")
    parser.add_argument("--clove-only", action="store_true", help="Only run Clove (single process)")
    parser.add_argument("--multiprocess-only", action="store_true", help="Only run Clove multi-process")
    parser.add_argument("--output", type=str, default="benchmark_results", help="Output directory")

    args = parser.parse_args()

    print("=" * 80)
    print("  RESEARCH TEAM BENCHMARK")
    print("  Comparing: LangGraph vs Clove vs Clove Multi-Process")
    print("=" * 80)
    print(f"\nTopic: {args.topic}")
    print(f"Iterations per framework: {args.iterations}")

    results = []

    # Check prerequisites
    clove_available = os.path.exists('/tmp/clove.sock')
    if not clove_available:
        print("\nWARNING: Clove kernel not running (/tmp/clove.sock not found)")
        print("Start with: ./build/clove_kernel")

    # Run LangGraph benchmark
    if not args.clove_only and not args.multiprocess_only:
        print("\n" + "-" * 40)
        print("LANGGRAPH BENCHMARK")
        print("-" * 40)
        try:
            result = run_langgraph_benchmark(args.topic, args.iterations)
            results.append(result)
        except Exception as e:
            print(f"  LangGraph benchmark failed: {e}")
            results.append({"framework": "langgraph", "error": str(e)})

    # Run Clove benchmark
    if clove_available and not args.langgraph_only and not args.multiprocess_only:
        print("\n" + "-" * 40)
        print("CLOVE BENCHMARK (Single Process)")
        print("-" * 40)
        try:
            result = run_clove_benchmark(args.topic, args.iterations)
            results.append(result)
        except Exception as e:
            print(f"  Clove benchmark failed: {e}")
            results.append({"framework": "clove", "error": str(e)})

    # Run Clove multi-process benchmark
    if clove_available and not args.langgraph_only and not args.clove_only:
        print("\n" + "-" * 40)
        print("CLOVE BENCHMARK (Multi-Process with IPC)")
        print("-" * 40)
        try:
            result = run_clove_multiprocess_benchmark(args.topic, args.iterations)
            results.append(result)
        except Exception as e:
            print(f"  Clove multi-process benchmark failed: {e}")
            results.append({"framework": "clove_multiprocess", "error": str(e)})

    # Print comparison
    if results:
        print_comparison(results)
        save_results(results, args.output)

    print("\nBenchmark complete!")
    return results


if __name__ == "__main__":
    main()
