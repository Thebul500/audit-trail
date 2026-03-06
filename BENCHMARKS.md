# API Performance Benchmarks

Benchmark results for the audit-trail API endpoints. All measurements use the FastAPI `TestClient` (in-process, no network overhead) with 1,000 requests per scenario after a 50-request warmup.

**Environment:**
- Python 3.x, FastAPI, Uvicorn
- In-process via `TestClient` (ASGI transport, no TCP)
- 1,000 requests per scenario, 50-request warmup

## Results Summary

| Scenario | Req/sec | p50 (ms) | p95 (ms) | p99 (ms) | Mean (ms) |
|---|---:|---:|---:|---:|---:|
| GET /health (sequential) | 1,162.6 | 0.842 | 1.289 | 1.512 | 0.857 |
| GET /ready (sequential) | 1,049.8 | 0.935 | 1.295 | 1.546 | 0.950 |
| GET /health (concurrent, 10 workers) | 1,083.5 | 8.587 | 15.062 | 19.091 | 8.936 |
| POST /nonexistent (404 handling) | 1,155.6 | 0.846 | 1.222 | 1.657 | 0.862 |

## Scenario Details

### 1. GET /health (Sequential)

Single-threaded serial requests to the health check endpoint, which returns status, version, and timestamp.

| Metric | Value |
|---|---:|
| Requests | 1,000 |
| Wall time | 0.860s |
| Requests/sec | 1,162.6 |
| p50 latency | 0.842ms |
| p95 latency | 1.289ms |
| p99 latency | 1.512ms |
| Min latency | 0.503ms |
| Max latency | 2.285ms |
| Mean | 0.857ms |
| Stdev | 0.279ms |

**Analysis:** Sub-millisecond median latency with tight distribution. The health endpoint performs datetime serialization and Pydantic model validation on every call. p99 stays under 2ms.

### 2. GET /ready (Sequential)

Single-threaded serial requests to the readiness probe, which returns a minimal JSON dict.

| Metric | Value |
|---|---:|
| Requests | 1,000 |
| Wall time | 0.953s |
| Requests/sec | 1,049.8 |
| p50 latency | 0.935ms |
| p95 latency | 1.295ms |
| p99 latency | 1.546ms |
| Min latency | 0.500ms |
| Max latency | 2.958ms |
| Mean | 0.950ms |
| Stdev | 0.246ms |

**Analysis:** Similar to /health. The readiness endpoint returns a plain dict (no Pydantic model), so overhead is dominated by ASGI transport and JSON serialization. Low variance confirms stable performance.

### 3. GET /health (Concurrent, 10 Workers)

10 threads sending requests concurrently to simulate load. 1,000 total requests split across workers.

| Metric | Value |
|---|---:|
| Requests | 1,000 |
| Wall time | 0.923s |
| Requests/sec | 1,083.5 |
| p50 latency | 8.587ms |
| p95 latency | 15.062ms |
| p99 latency | 19.091ms |
| Min latency | 0.842ms |
| Max latency | 23.597ms |
| Mean | 8.936ms |
| Stdev | 3.331ms |

**Analysis:** Per-request latency rises ~10x under concurrency due to GIL contention and thread scheduling in the synchronous TestClient. Throughput (req/sec) remains comparable to sequential because wall clock time accounts for parallelism. In production with async workers and network I/O, concurrent latency would be significantly lower.

### 4. POST /nonexistent (404 Error Handling)

Measures FastAPI's routing and error response path for unmatched routes.

| Metric | Value |
|---|---:|
| Requests | 1,000 |
| Wall time | 0.865s |
| Requests/sec | 1,155.6 |
| p50 latency | 0.846ms |
| p95 latency | 1.222ms |
| p99 latency | 1.657ms |
| Min latency | 0.474ms |
| Max latency | 3.882ms |
| Mean | 0.862ms |
| Stdev | 0.267ms |

**Analysis:** 404 error handling is as fast as successful responses. FastAPI's router lookup fails quickly and returns a standard error response with minimal overhead.

## Key Takeaways

1. **Sub-millisecond median latency** across all sequential scenarios — the API responds in under 1ms at p50.
2. **Consistent p99 under 2ms** for sequential requests, indicating predictable tail latency.
3. **Error paths are not slower** than success paths — 404 handling adds no measurable overhead.
4. **Concurrent load increases per-request latency** (expected with TestClient's synchronous transport) but total throughput remains stable at ~1,000+ req/sec.

## Reproducing

```bash
# From project root
python -m benchmarks.bench_api
```

The script outputs both human-readable tables and JSON for programmatic use.
