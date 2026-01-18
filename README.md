# LLM MedGen Tool

複数のLLMによるデータ生成を1クリックで行えるツールです。

## 機能

- **複数LLMの並列生成**: OpenAI GPT-4.1とOllama上の複数モデルで同時にデータ生成
- **ストリーミング出力**: リアルタイムでテキスト生成を表示
- **パフォーマンス可視化**: 各モデルのTTFT, TPS, TPOT, ITLを表示
- **ファイルアップロード**: テキストファイル（.txt, .md, .csv）のドラッグ&ドロップ読み込み
- **自動評価**: OpenAIの高パラメータモデルによる出力結果の多角的評価
- **日本語UI**: 直感的な日本語インターフェース
- **Docker対応**: Docker Composeで簡単に起動

## パフォーマンスメトリクス

各モデルウィンドウに以下のメトリクスを表示：

| 指標 | 説明 | 単位 |
|------|------|------|
| **TTFT** | 最初のトークンが出力されるまでの時間 | ms |
| **TPS** | トークン生成速度 | tok/s |
| **TPOT** | 1トークン出力にかかる時間 | ms/token |
| **ITL** | トークン間隔の平均 | ms |

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **フロントエンド**: React (TypeScript) + Vite
- **コンテナ**: Docker & Docker Compose

## セットアップ

### 1. 環境変数の設定

`env.example`をコピーして`.env`ファイルを作成し、必要な情報を設定してください：

```bash
cp env.example .env
```

`.env`ファイルの内容：

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EVAL_MODEL=gpt-4o
OLLAMA_SERVER_URL=http://your-ollama-server:11434
```

### 2. Docker Composeで起動

```bash
docker-compose up -d --build
```

### 3. アクセス

- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- APIドキュメント: http://localhost:8000/docs

## 使用方法

1. **入力テキストを入力**: テキストエリアに入力するか、ファイルをドラッグ&ドロップ
2. **Ollamaモデルを選択**: ドロップダウンから最大2つのモデルを選択
3. **生成を実行**: 「全ウィンドウで生成を実行」ボタンをクリック
4. **結果を確認**: 各ウィンドウにリアルタイムで出力とメトリクスが表示

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/api/ollama/models` | GET | Ollamaモデル一覧取得 |
| `/api/generate` | POST | 並列生成（非ストリーミング） |
| `/api/generate-stream` | POST | ストリーミング生成（SSE） |
| `/api/evaluate` | POST | 出力結果を評価 |
| `/api/generate-and-evaluate` | POST | 生成と評価を一括実行 |
| `/api/upload` | POST | ファイルアップロード |

## 注意事項

- Ollamaサーバーは事前に起動し、指定されたURLでアクセス可能である必要があります
- OpenAI APIキーが必要です
- 並列処理により、複数のLLMが同時に実行されます
