# LLM MedGen Tool 仕様書

## プロジェクト概要

複数のLLMによるデータ生成を1クリックで行えるツールです。OpenAI GPT-4.1とOllama上の複数モデル（最大2つ選択可能）で並列生成を行い、OpenAIの高パラメータモデルで出力結果を評価します。

## 機能要件

### 1. LLM生成機能

以下のLLMを使用してデータ生成を実行：

- **OpenAI GPT-4.1**: API経由で使用（必須・固定）
- **ローカルLLMバックエンド**:
  - **Ollama**: MedGemma, Gemma3 27b, gpt-oss:120b 等
  - **vLLM**: OpenAI互換 APIでアクセス

### 2. 並列処理

- すべてのLLM生成は並列処理で実行
- 同じ入力テキストをすべてのモデルに送信
- 各モデルの出力を個別に取得

### 3. 評価機能

- OpenAIの高パラメータモデル（デフォルト: gpt-4o）を使用
- 以下の観点から評価：
  - 各出力の正確性（事実誤認がないか）
  - 各出力間の差異分析
  - 品質スコア（1-10点）
  - 推奨される出力
  - 改善点

### 4. ストリーミング出力

- Server-Sent Events (SSE) によるリアルタイム出力
- 各モデルの出力を並列でストリーミング
- ストリーミング中のカーソルアニメーション

### 5. パフォーマンス可視化

各モデルウィンドウに以下のメトリクスを表示：

| 指標 | 説明 | 単位 |
|------|------|------|
| **TTFT** | 最初のトークンまでの時間 | ms |
| **TPS** | トークン生成速度 | tok/s |
| **TPOT** | 1トークンあたりの時間 | ms/token |
| **ITL** | トークン間隔の平均 | ms |

### 6. ファイルアップロード

- 対応形式: `.txt`, `.md`, `.csv`
- ドラッグ&ドロップ対応
- UTF-8 / Shift-JIS 自動判別

### 7. UI要件 (3ウィンドウ構成)

- **レイアウト**: 3列のカラム構成
  1. **左**: OpenAI GPT-4.1 (固定表示)
  2. **中**: ローカルモデル 1 (バックエンド選択 + モデル選択)
  3. **右**: ローカルモデル 2 (バックエンド選択 + モデル選択)
- **操作**:
  - 入力テキストエリア（ファイルD&D対応）
  - ファイル選択ボタン
  - Ollama/vLLM 切り替えボタン（各ウィンドウ）
  - 「全ウィンドウで生成を実行」ボタン
- **表示**:
  - 各ウィンドウ内にストリーミング出力
  - 各ウィンドウ下部にパフォーマンスメトリクス
  - 画面下部に評価結果を表示

### 8. デュアルバックエンド対応

- **UI切り替え**: 各ウィンドウでOllama/vLLMをボタンで切り替え
- **同時実行**: 異なるバックエンドを同時に使用可能
- **動的モデルリスト**: バックエンド切り替え時にモデル一覧を更新

## 技術仕様

### アーキテクチャ

- **バックエンド**: FastAPI (Python 3.11)
- **フロントエンド**: React 18 (TypeScript)
- **ビルドツール**: **Vite**
- **コンテナ**: Docker & Docker Compose
- **環境変数管理**: .envファイル

### バックエンドAPI

#### エンドポイント

1. `GET /api/ollama/models`
   - 利用可能なOllamaモデル一覧を取得（後方互換）
   - レスポンス: `{"models": ["model1", "model2", ...]}`

2. `GET /api/all-models`
   - OllamaとvLLM両方のモデル一覧を取得
   - レスポンス: `{"ollama": [...], "vllm": [...]}`

3. `POST /api/generate-stream`
   - ストリーミング生成（SSE）
   - リクエスト: `{"input_text": "...", "local_models": [{"model": "...", "backend": "ollama|vllm"}]}`
   - レスポンス: SSEイベント（partial, complete, done）

4. `POST /api/generate-and-evaluate`
   - 生成と評価の一括実行
   - リクエスト: `{"input_text": "...", "local_models": [...]}`
   - レスポンス: `{"outputs": {...}, "evaluation": {...}}`

5. `POST /api/upload`
   - ファイルアップロード
   - リクエスト: `multipart/form-data`
   - レスポンス: `{"content": "...", "filename": "..."}`

### 環境変数

`.env`ファイルに以下の設定が必要：

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EVAL_MODEL=gpt-4o
OLLAMA_SERVER_URL=http://172.19.201.221:11434
VLLM_SERVER_URL=http://172.19.201.221/vllm
LOCAL_LLM_BACKEND=ollama  # デフォルトバックエンド（オプション）
```

### ディレクトリ構造

```
LLMMedGen/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── package.json (Vite仕様)
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html (Project Root)
│   └── src/
│       ├── App.tsx
│       ├── App.css
│       └── index.tsx
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md
```

## 非機能要件

- Docker環境で動作
- 並列処理による高速化
- エラーハンドリング
- CORS設定（フロントエンドとバックエンドの通信）
- Windows環境でのDockerファイル同期対応 (Vite Polling有効)

## 制約事項

- Ollamaサーバーは社内指定サーバー上で動作（デフォルト: 172.19.201.221:11434）
- バックエンドコンテナからのネットワーク疎通に注意が必要（IP競合の可能性あり）
