# LLM MedGen Tool 環境構築手順書

## 前提条件

- Docker Desktop がインストールされていること
- Git がインストールされていること
- OpenAI API キーを取得済みであること
- Ollama サーバーへのネットワークアクセスが可能であること

---

## 環境構築手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd LLMMedGen
```

### 2. 環境変数の設定

```bash
cp env.example .env
```

`.env` ファイルを編集:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_EVAL_MODEL=gpt-4o
OLLAMA_SERVER_URL=http://172.19.201.221:11434
VLLM_SERVER_URL=http://172.19.201.221/vllm
LOCAL_LLM_BACKEND=ollama
```

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `OPENAI_API_KEY` | OpenAI API キー | `sk-xxx...` |
| `OPENAI_EVAL_MODEL` | 評価に使用するモデル | `gpt-4o` |
| `OLLAMA_SERVER_URL` | Ollama サーバー URL | `http://172.19.201.221:11434` |
| `VLLM_SERVER_URL` | vLLM サーバー URL | `http://172.19.201.221/vllm` |
| `LOCAL_LLM_BACKEND` | デフォルトバックエンド | `ollama` or `vllm` |

### 3. Docker コンテナの起動

```bash
docker-compose up -d --build
```

### 4. 動作確認

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント**: http://localhost:8000/docs

---

## よくあるトラブルと対処法

### モデル一覧が表示されない

**原因**: Ollama サーバーへの接続失敗

```bash
# バックエンドログを確認
docker-compose logs backend

# Ollama サーバーの疎通確認
curl http://172.19.201.221:11434/api/tags
```

**対処**: `.env` の `OLLAMA_SERVER_URL` を確認

### OpenAI API エラー

**原因**: API キーの設定ミス

**対処**: `.env` の `OPENAI_API_KEY` を確認

### ファイル変更が反映されない (Windows)

**対処**: コンテナを再起動

```bash
docker-compose down
docker-compose up -d --build
```

---

## コマンドリファレンス

| 操作 | コマンド |
|------|----------|
| 起動 | `docker-compose up -d` |
| 起動 (ビルド込み) | `docker-compose up -d --build` |
| 停止 | `docker-compose down` |
| ログ確認 | `docker-compose logs -f` |
| バックエンドログ | `docker-compose logs backend` |
| フロントエンドログ | `docker-compose logs frontend` |
| 再起動 | `docker-compose restart` |

---

## ディレクトリ構造

```
LLMMedGen/
├── backend/
│   ├── Dockerfile
│   ├── main.py          # FastAPI アプリケーション
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx      # メインコンポーネント
│       └── App.css
├── doc/
│   ├── SETUP.md         # この手順書
│   ├── SPECIFICATION.md # 仕様書
│   └── HANDOVER.md      # 引継ぎドキュメント
├── docker-compose.yml
├── .env                 # 環境変数（要作成）
└── README.md
```
