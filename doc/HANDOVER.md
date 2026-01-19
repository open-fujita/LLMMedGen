# 引き継ぎドキュメント

## プロジェクト概要

LLM MedGen Tool - 複数のLLMによるデータ生成と評価ツール

## 現在の状態

### 動作しているもの

1. **バックエンドAPI**
   - 状態: ✅ 正常に起動中
   - URL: http://localhost:8000
   - APIドキュメント: http://localhost:8000/docs
   - コンテナ名: `llmmedgen-backend-1`

2. **フロントエンド**
   - 状態: ✅ 正常に起動中 (Vite移行完了)
   - URL: http://localhost:3000
   - コンテナ名: `llmmedgen-frontend-1`

3. **Docker環境**
   - Docker Compose: 正常に動作

### 問題が発生していたもの（解決済み）

1. **バックエンドからOllamaサーバーへの接続**
   - 状態: ✅ 解決済み
   - 対応: `.env`に`OLLAMA_SERVER_URL=http://172.19.201.221:11434`を設定

2. **OpenAI APIモデル名**
   - 状態: ✅ 解決済み
   - 対応: `gpt-4-turbo-preview`（廃止）を`gpt-4o`に更新

## 実施した作業内容（2026年1月17日）

### 実施した対応（完了）

1. **ストリーミング出力の実装**
   - バックエンド: `sse-starlette`パッケージを追加し、`/api/generate-stream`エンドポイントを新規作成
   - OpenAI API、Ollama APIのストリーミング対応関数を追加
   - フロントエンド: fetch + ReadableStreamでSSEを受信し、各ウィンドウにリアルタイム表示
   - ストリーミング中のカーソルアニメーションを追加

2. **パフォーマンス可視化機能**
   - 各モデルウィンドウにパフォーマンスメトリクス（TTFT, TPS, TPOT, ITL）を表示
   - バックエンドでストリーミング中にメトリクス計算を実施
   - メトリクスパネルをウィンドウ下部に追加

3. **ファイルアップロード機能**
   - `/api/upload`エンドポイントを追加（`.txt`, `.md`, `.csv`対応）
   - ドラッグ＆ドロップでファイル読み込み可能
   - ファイル選択ボタンからもアップロード可能

## 実施した作業内容（2026年1月16日）

### 実施した対応（完了）

1. **フロントエンドのVite移行**
   - `react-scripts` から `vite` へビルドツールを移行
   - 依存関係エラー（ajv）を解消
   - Dockerfileを更新し、開発サーバー（`npm run dev`）で起動するように変更

2. **UI刷新（3ウィンドウ構成）**
   - 画面を3列に分割（GPT-4.1固定 + ローカル選択 x 2）
   - 全ウィンドウ同時生成機能の実装

3. **ファイル同期問題への対応**
   - Windows Docker環境向けにViteのポーリング設定（`usePolling: true`）を追加

### 実施した対応（解決済み）

1. **Ollama接続問題の解決**
   - `docker-compose.yml`に`extra_hosts`設定を追加
   - `.env`に正しい`OLLAMA_SERVER_URL`を設定

2. **OpenAI APIモデル更新**
   - `backend/main.py`のモデル名を`gpt-4-turbo-preview`から`gpt-4o`に変更

3. **ファイル同期問題への対応**
   - Windows Docker環境向けにViteのポーリング設定（`usePolling: true`）を追加

4. **デュアルバックエンド対応 (2026-01-19)**
   - OllamaとvLLMをUIで切り替え可能に
   - 各ウィンドウで独立してバックエンド選択（Ollama/vLLMボタン）
   - 両バックエンドを同時に使用可能
   - `/api/all-models`エンドポイント追加（両バックエンドのモデル一覧取得）
   - `LocalModelRequest`でモデルごとにバックエンド指定
   - `feature/vllm-support`ブランチで開発

## 次のステップ（予定）

1. **生成結果のエクスポート機能**
   - 生成結果をJSON/CSVでダウンロード

## コマンドリファレンス

### Docker Compose操作

```bash
# 環境の起動
docker-compose up -d

# 環境の停止
docker-compose down

# ログの確認
docker-compose logs -f
```

## 技術スタック（更新済み）

- **バックエンド**: FastAPI (Python 3.11)
- **フロントエンド**: React 18.2.0 + TypeScript
- **ビルドツール**: **Vite** (Create React Appから移行済み)
- **コンテナ**: Docker & Docker Compose