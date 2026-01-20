from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, AsyncGenerator
import asyncio
import httpx
import os
import json
import time
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse

load_dotenv()

app = FastAPI(title="LLM MedGen Tool", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数の読み込み
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL", "http://localhost:11434")
VLLM_SERVER_URL = os.getenv("VLLM_SERVER_URL", "http://localhost:8080")
LOCAL_LLM_BACKEND = os.getenv("LOCAL_LLM_BACKEND", "ollama")  # "ollama" or "vllm"
OPENAI_EVAL_MODEL = os.getenv("OPENAI_EVAL_MODEL", "gpt-4o")

# リクエストモデル
class LocalModelRequest(BaseModel):
    model: str
    backend: str  # "ollama" or "vllm"

class GenerationRequest(BaseModel):
    input_text: str
    local_models: List[LocalModelRequest] = []  # バックエンド指定付きモデル
    ollama_models: List[str] = []  # 後方互換性のため残す


class EvaluationRequest(BaseModel):
    input_text: str
    outputs: Dict[str, str]  # モデル名: 出力テキスト

# OpenAI API呼び出し
async def call_openai_gpt4(prompt: str) -> str:
    """OpenAI GPT-4.1を呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API エラー: {str(e)}")

# OpenAI API ストリーミング呼び出し
async def call_openai_gpt4_stream(prompt: str) -> AsyncGenerator[str, None]:
    """OpenAI GPT-4.1をストリーミングモードで呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f"[エラー: {str(e)}]"

# Ollama API呼び出し
async def call_ollama(model: str, prompt: str) -> str:
    """Ollamaモデルを呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_SERVER_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama API エラー ({model}): {str(e)}")

# Ollama API ストリーミング呼び出し
async def call_ollama_stream(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """Ollamaモデルをストリーミングモードで呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_SERVER_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("response", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f"[エラー: {str(e)}]"

# vLLM API呼び出し（OpenAI互換API）
async def call_vllm(model: str, prompt: str) -> str:
    """vLLMモデルを呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{VLLM_SERVER_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"vLLM API エラー ({model}): {str(e)}")

# vLLM API ストリーミング呼び出し
async def call_vllm_stream(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """vLLMモデルをストリーミングモードで呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{VLLM_SERVER_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield f"[エラー: {str(e)}]"

# 統合ローカルLLM呼び出し（バックエンド指定対応）
async def call_local_llm_stream(model: str, prompt: str, backend: str = None) -> AsyncGenerator[str, None]:
    """指定されたバックエンドでローカルLLMを呼び出し"""
    use_backend = backend if backend else LOCAL_LLM_BACKEND
    if use_backend == "vllm":
        async for chunk in call_vllm_stream(model, prompt):
            yield chunk
    else:
        async for chunk in call_ollama_stream(model, prompt):
            yield chunk


# ストリームジェネレーター
async def stream_generator(input_text: str, local_models: List[LocalModelRequest] = None, ollama_models: List[str] = None) -> AsyncGenerator[dict, None]:
    """すべてのLLMの出力をSSEイベントとしてストリーミング（パフォーマンスメトリクス付き）"""""
    
    # 各モデルのストリーミングタスクを管理
    model_full_outputs = {}
    
    # OpenAI GPT-4.1 タスク（メトリクス計測付き）
    async def stream_openai():
        full_output = ""
        token_count = 0
        start_time = time.time()
        first_token_time = None
        token_times = []
        last_token_time = start_time
        
        async for chunk in call_openai_gpt4_stream(input_text):
            current_time = time.time()
            if first_token_time is None:
                first_token_time = current_time
            else:
                token_times.append((current_time - last_token_time) * 1000)
            last_token_time = current_time
            
            full_output += chunk
            token_count += 1
            yield {"model": "OpenAI GPT-4.1", "type": "partial", "content": chunk}
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
        tps = token_count / (end_time - start_time) if (end_time - start_time) > 0 else 0
        tpot_ms = 1000 / tps if tps > 0 else 0
        itl_avg_ms = sum(token_times) / len(token_times) if token_times else 0
        
        model_full_outputs["OpenAI GPT-4.1"] = full_output
        yield {
            "model": "OpenAI GPT-4.1", 
            "type": "complete", 
            "content": full_output,
            "metrics": {
                "ttft_ms": round(ttft_ms, 1),
                "tps": round(tps, 1),
                "tpot_ms": round(tpot_ms, 1),
                "itl_avg_ms": round(itl_avg_ms, 1),
                "total_tokens": token_count,
                "total_time_ms": round(total_time_ms, 1)
            }
        }
    
    # ローカルモデル タスク（メトリクス計測付き）- Ollama/vLLM両対応
    async def stream_local_model(model_name: str, backend: str = None):
        full_output = ""
        token_count = 0
        start_time = time.time()
        first_token_time = None
        token_times = []
        last_token_time = start_time
        
        async for chunk in call_local_llm_stream(model_name, input_text, backend):
            current_time = time.time()
            if first_token_time is None:
                first_token_time = current_time
            else:
                token_times.append((current_time - last_token_time) * 1000)
            last_token_time = current_time
            
            full_output += chunk
            token_count += 1
            yield {"model": model_name, "type": "partial", "content": chunk}
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
        tps = token_count / (end_time - start_time) if (end_time - start_time) > 0 else 0
        tpot_ms = 1000 / tps if tps > 0 else 0
        itl_avg_ms = sum(token_times) / len(token_times) if token_times else 0
        
        model_full_outputs[model_name] = full_output
        yield {
            "model": model_name, 
            "type": "complete", 
            "content": full_output,
            "metrics": {
                "ttft_ms": round(ttft_ms, 1),
                "tps": round(tps, 1),
                "tpot_ms": round(tpot_ms, 1),
                "itl_avg_ms": round(itl_avg_ms, 1),
                "total_tokens": token_count,
                "total_time_ms": round(total_time_ms, 1)
            }
        }
    
    # すべてのジェネレーターを作成
    generators = [stream_openai()]
    
    # 新形式: LocalModelRequest リスト
    if local_models:
        for lm in local_models:
            if lm.model:
                generators.append(stream_local_model(lm.model, lm.backend))
    
    # 後方互換: ollama_models リスト
    if ollama_models:
        for model in ollama_models:
            if model:
                generators.append(stream_local_model(model, None))
    
    # 並列でストリーミング（各ジェネレーターからのイベントをマージ）
    async def merge_generators():
        tasks = {}
        pending = set()
        
        for i, gen in enumerate(generators):
            task = asyncio.create_task(gen.__anext__())
            tasks[task] = (i, gen)
            pending.add(task)
        
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                idx, gen = tasks.pop(task)
                try:
                    result = task.result()
                    yield result
                    
                    # 次のチャンクを取得
                    next_task = asyncio.create_task(gen.__anext__())
                    tasks[next_task] = (idx, gen)
                    pending.add(next_task)
                except StopAsyncIteration:
                    # このジェネレーターは終了
                    pass
                except Exception as e:
                    yield {"model": f"Generator {idx}", "type": "error", "content": str(e)}
    
    async for event in merge_generators():
        yield {"data": json.dumps(event, ensure_ascii=False)}
    
    # 完了イベント
    yield {"data": json.dumps({"type": "done"}, ensure_ascii=False)}

# 並列生成処理
async def generate_all_parallel(input_text: str, ollama_models: List[str]) -> Dict[str, str]:
    """すべてのLLMで並列に生成"""
    tasks = []
    
    # OpenAI GPT-4.1
    tasks.append(("OpenAI GPT-4.1", call_openai_gpt4(input_text)))
    
    # Ollamaモデル
    for model in ollama_models:
        tasks.append((model, call_ollama(model, input_text)))
    
    # 並列実行
    results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
    
    # 結果を辞書にまとめる
    output_dict = {}
    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            output_dict[name] = f"エラー: {str(result)}"
        else:
            output_dict[name] = result
    
    return output_dict

# 評価処理
async def evaluate_outputs(input_text: str, outputs: Dict[str, str]) -> Dict[str, Any]:
    """OpenAIの高パラメータモデルで出力を評価"""
    # 評価プロンプトの作成
    outputs_text = "\n\n".join([f"【{model}】\n{output}" for model, output in outputs.items()])
    
    evaluation_prompt = f"""以下の入力テキストに対して、複数のLLMが生成した出力を評価してください。

【入力テキスト】
{input_text}

【各LLMの出力】
{outputs_text}

以下の観点から評価を行い、JSON形式で回答してください：
1. 各出力の正確性（事実誤認がないか）
2. 各出力間の差異分析
3. 品質スコア（1-10点）
4. 推奨される出力
5. 改善点
6. 改善プロンプト（課題を解決するための具体的なプロンプト例を3つ提案してください。各プロンプトは、出力の課題となっている部分を改善するためのものです）

JSON形式で回答してください。改善プロンプトは以下の形式で含めてください：
{{
  "各出力の正確性": {{ ... }},
  "差異分析": "...",
  "品質スコア": {{ ... }},
  "推奨される出力": "...",
  "改善点": "...",
  "改善プロンプト": [
    "改善プロンプト1の内容",
    "改善プロンプト2の内容",
    "改善プロンプト3の内容"
  ]
}}"""

    try:
        evaluation_result = await call_openai_gpt4(evaluation_prompt)
        return {
            "evaluation": evaluation_result,
            "evaluator_model": OPENAI_EVAL_MODEL
        }
    except Exception as e:
        return {
            "evaluation": f"評価エラー: {str(e)}",
            "evaluator_model": OPENAI_EVAL_MODEL
        }

@app.get("/")
async def root():
    return {"message": "LLM MedGen Tool API"}

@app.get("/api/ollama/models")
async def get_ollama_models():
    """利用可能なOllamaモデル一覧を取得（後方互換性）"""
    return await get_local_models()

@app.get("/api/local/models")
async def get_local_models():
    """現在のバックエンドで利用可能なモデル一覧を取得"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if LOCAL_LLM_BACKEND == "vllm":
                response = await client.get(f"{VLLM_SERVER_URL}/v1/models")
                response.raise_for_status()
                data = response.json()
                models = [model["id"] for model in data.get("data", [])]
            else:
                response = await client.get(f"{OLLAMA_SERVER_URL}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
            return {"models": models, "backend": LOCAL_LLM_BACKEND}
    except Exception as e:
        return {"models": [], "backend": LOCAL_LLM_BACKEND, "error": str(e)}

@app.get("/api/local/backend")
async def get_backend_info():
    """現在のバックエンド設定情報を取得"""
    return {
        "backend": LOCAL_LLM_BACKEND,
        "ollama_url": OLLAMA_SERVER_URL,
        "vllm_url": VLLM_SERVER_URL
    }

@app.get("/api/all-models")
async def get_all_models():
    """OllamaとvLLM両方のモデル一覧を取得"""
    ollama_models = []
    vllm_models = []
    
    # Ollamaモデル取得
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_SERVER_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
            ollama_models = [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"Ollama models error: {e}")
    
    # vLLMモデル取得
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VLLM_SERVER_URL}/v1/models")
            response.raise_for_status()
            data = response.json()
            vllm_models = [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"vLLM models error: {e}")
    
    return {
        "ollama": ollama_models,
        "vllm": vllm_models
    }

@app.post("/api/generate")
async def generate(request: GenerationRequest):
    """複数のLLMで並列生成"""
    try:
        results = await generate_all_parallel(request.input_text, request.ollama_models)
        return {"outputs": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-stream")
async def generate_stream(request: GenerationRequest):
    """ストリーミングで並列生成"""
    return EventSourceResponse(
        stream_generator(request.input_text, request.local_models, request.ollama_models)
    )

@app.post("/api/evaluate")
async def evaluate(request: EvaluationRequest):
    """出力結果を評価"""
    try:
        evaluation = await evaluate_outputs(request.input_text, request.outputs)
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-and-evaluate")
async def generate_and_evaluate(request: GenerationRequest):
    """生成と評価を一括実行"""
    try:
        # 並列生成
        outputs = await generate_all_parallel(request.input_text, request.ollama_models)
        
        # 評価
        evaluation = await evaluate_outputs(request.input_text, outputs)
        
        return {
            "outputs": outputs,
            "evaluation": evaluation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """テキストファイルをアップロードして内容を取得"""
    # 許可する拡張子
    allowed_extensions = [".txt", ".md", ".csv"]
    filename = file.filename or ""
    
    # 拡張子チェック
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"許可されていないファイル形式です。対応形式: {', '.join(allowed_extensions)}"
        )
    
    try:
        content = await file.read()
        # UTF-8でデコード、失敗したらShift-JISを試行
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("shift-jis")
        
        return {"content": text, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル読み込みエラー: {str(e)}")
