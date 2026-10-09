"""Prueba de carga ligera de POST /ingest/commit (bajo demanda, no en cada push).

Presupuesto para uso personal: 0 errores y p95 por debajo de P95_BUDGET_MS con CONCURRENCY
clientes simultáneos. Contra el stack local:  just load   (API + worker + infra arriba)
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
import uuid

import httpx

P95_BUDGET_MS = 300.0


async def main(args: argparse.Namespace) -> int:
    run = uuid.uuid4().hex[:8]
    latencies: list[float] = []
    errors: list[str] = []
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(args.requests):
        queue.put_nowait(i)

    async def worker(client: httpx.AsyncClient) -> None:
        while not queue.empty():
            i = queue.get_nowait()
            body = {
                "project": args.project,
                "ref": "refs/heads/load",
                "head_sha": f"load-{run}-{i}",
                "title": "carga",
                "author": "load",
                "diff": "diff --git a/x b/x\n" + "+línea\n" * 200,
            }
            start = time.perf_counter()
            try:
                response = await client.post("/ingest/commit", json=body)
                if response.status_code != 202:
                    errors.append(f"HTTP {response.status_code}")
            except httpx.HTTPError as exc:
                errors.append(type(exc).__name__)
            latencies.append((time.perf_counter() - start) * 1000)

    headers = {"X-Ingest-Token": args.token}
    async with httpx.AsyncClient(base_url=args.url, headers=headers, timeout=30) as client:
        started = time.perf_counter()
        await asyncio.gather(*(worker(client) for _ in range(args.concurrency)))
        elapsed = time.perf_counter() - started

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(
        f"{len(latencies)} peticiones, concurrencia {args.concurrency}, "
        f"{len(latencies) / elapsed:.0f} req/s | p50 {statistics.median(latencies):.0f} ms, "
        f"p95 {p95:.0f} ms, máx {latencies[-1]:.0f} ms | errores: {len(errors)}"
    )
    if errors or p95 > P95_BUDGET_MS:
        print(f"PRESUPUESTO EXCEDIDO (p95 <= {P95_BUDGET_MS:.0f} ms, 0 errores)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--project", default="demo/repo")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=5)
    sys.exit(asyncio.run(main(parser.parse_args())))
