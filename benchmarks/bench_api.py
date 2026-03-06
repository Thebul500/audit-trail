"""API performance benchmarks for audit-trail.

Measures requests/sec, p50/p95/p99 latency for key endpoints.
Uses FastAPI TestClient for in-process benchmarking (no network overhead).
"""

import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from audit_trail.app import create_app

NUM_REQUESTS = 1000
CONCURRENT_WORKERS = 10


def measure_latencies(client: TestClient, method: str, path: str, num: int, **kwargs) -> list[float]:
    """Send num requests and return list of latencies in ms."""
    latencies = []
    for _ in range(num):
        start = time.perf_counter()
        resp = client.request(method, path, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code in (200, 201, 404, 422), f"Unexpected {resp.status_code}"
        latencies.append(elapsed_ms)
    return latencies


def measure_concurrent(
    client: TestClient, method: str, path: str, total: int, workers: int, **kwargs
) -> list[float]:
    """Send total requests across worker threads, return latencies in ms."""
    latencies: list[float] = []
    per_worker = total // workers

    def worker_fn():
        local = []
        for _ in range(per_worker):
            start = time.perf_counter()
            resp = client.request(method, path, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code in (200, 201, 404, 422)
            local.append(elapsed_ms)
        return local

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker_fn) for _ in range(workers)]
        for f in as_completed(futures):
            latencies.extend(f.result())

    return latencies


def compute_stats(latencies: list[float], wall_time_s: float) -> dict:
    """Compute percentile stats and requests/sec."""
    latencies.sort()
    n = len(latencies)
    return {
        "requests": n,
        "wall_time_s": round(wall_time_s, 3),
        "requests_per_sec": round(n / wall_time_s, 1),
        "p50_ms": round(latencies[int(n * 0.50)], 3),
        "p95_ms": round(latencies[int(n * 0.95)], 3),
        "p99_ms": round(latencies[int(n * 0.99)], 3),
        "min_ms": round(latencies[0], 3),
        "max_ms": round(latencies[-1], 3),
        "mean_ms": round(statistics.mean(latencies), 3),
        "stdev_ms": round(statistics.stdev(latencies), 3) if n > 1 else 0,
    }


def run_scenario(name: str, fn, *args, **kwargs) -> dict:
    """Run a benchmark scenario and return stats."""
    # Warmup
    print(f"  Warming up {name}...", flush=True)
    fn(*args, num=50, **{k: v for k, v in kwargs.items() if k != "num"})

    print(f"  Running {name}...", flush=True)
    wall_start = time.perf_counter()
    latencies = fn(*args, **kwargs)
    wall_time = time.perf_counter() - wall_start

    stats = compute_stats(latencies, wall_time)
    stats["scenario"] = name
    return stats


def main():
    app = create_app()
    results = []

    with TestClient(app) as client:
        # Scenario 1: GET /health — sequential
        stats = run_scenario(
            "GET /health (sequential)",
            measure_latencies,
            client, "GET", "/health",
            num=NUM_REQUESTS,
        )
        results.append(stats)

        # Scenario 2: GET /ready — sequential
        stats = run_scenario(
            "GET /ready (sequential)",
            measure_latencies,
            client, "GET", "/ready",
            num=NUM_REQUESTS,
        )
        results.append(stats)

        # Scenario 3: GET /health — concurrent (10 workers)
        print(f"  Warming up concurrent...", flush=True)
        measure_concurrent(client, "GET", "/health", total=100, workers=CONCURRENT_WORKERS)

        print(f"  Running concurrent...", flush=True)
        wall_start = time.perf_counter()
        latencies = measure_concurrent(
            client, "GET", "/health",
            total=NUM_REQUESTS, workers=CONCURRENT_WORKERS,
        )
        wall_time = time.perf_counter() - wall_start
        stats = compute_stats(latencies, wall_time)
        stats["scenario"] = f"GET /health (concurrent, {CONCURRENT_WORKERS} workers)"
        results.append(stats)

        # Scenario 4: POST to non-existent endpoint (error handling)
        stats = run_scenario(
            "POST /nonexistent (404 error handling)",
            measure_latencies,
            client, "POST", "/nonexistent",
            num=NUM_REQUESTS,
        )
        results.append(stats)

    # Print results
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    for r in results:
        print(f"\n--- {r['scenario']} ---")
        print(f"  Requests:     {r['requests']}")
        print(f"  Wall time:    {r['wall_time_s']}s")
        print(f"  Req/sec:      {r['requests_per_sec']}")
        print(f"  Latency p50:  {r['p50_ms']}ms")
        print(f"  Latency p95:  {r['p95_ms']}ms")
        print(f"  Latency p99:  {r['p99_ms']}ms")
        print(f"  Min:          {r['min_ms']}ms")
        print(f"  Max:          {r['max_ms']}ms")
        print(f"  Mean:         {r['mean_ms']}ms")
        print(f"  Stdev:        {r['stdev_ms']}ms")

    # Dump JSON for programmatic use
    print("\n\n--- JSON ---")
    print(json.dumps(results, indent=2))

    return results


if __name__ == "__main__":
    main()
