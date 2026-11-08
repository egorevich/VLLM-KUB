import json
import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

VLLM_URL = os.getenv("VLLM_URL", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("VLLM_API_KEY", "test-secret-token")


class BenchmarkRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int = 256


@app.post("/benchmark")
async def benchmark(req: BenchmarkRequest):
    payload = {
        "model": req.model,
        "messages": [
            {"role": "user", "content": req.prompt}
        ],
        "max_tokens": req.max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True}
    }

    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    start = time.perf_counter()
    ttft = None
    previous_chunk_time = None
    chunk_intervals = []
    prompt_tokens = 0
    completion_tokens = 0

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{VLLM_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="vLLM request failed"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = line[6:]

                    if data == "[DONE]":
                        break

                    chunk = json.loads(data)

                    # Последний chunk может содержать статистику usage
                    usage = chunk.get("usage")

                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get(
                            "completion_tokens", 0
                        )

                    choices = chunk.get("choices", [])

                    if not choices:
                        continue

                    content = choices[0].get("delta", {}).get("content")

                    if content:
                        now = time.perf_counter()

                        if ttft is None:
                            ttft = now - start
                        else:
                            chunk_intervals.append(
                                now - previous_chunk_time
                            )

                        previous_chunk_time = now

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Cannot connect to vLLM"
        )

    total_time = time.perf_counter() - start

    generation_time = (
        total_time - ttft if ttft is not None else None
    )

    itl = (
        sum(chunk_intervals) / len(chunk_intervals)
        if chunk_intervals else None
    )

    tokens_per_second = (
        completion_tokens / generation_time
        if generation_time and generation_time > 0
        else None
    )

    result = {
        "model": req.model,
        "max_tokens": req.max_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "ttft_seconds": round(ttft, 4) if ttft is not None else None,
        "itl_seconds": round(itl, 4) if itl is not None else None,
        "tokens_per_second": (
            round(tokens_per_second, 2)
            if tokens_per_second is not None else None
        ),
        "total_time_seconds": round(total_time, 4)
    }

    print("Benchmark completed:", {
        key: value
        for key, value in result.items()
        if key != "model"
    })

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
