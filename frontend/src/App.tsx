import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ModelOutput {
  [modelName: string]: string;
}

interface EvaluationResult {
  evaluation: string;
  evaluator_model: string;
}

interface StreamingState {
  [modelName: string]: boolean;
}

interface PerformanceMetrics {
  ttft_ms: number;
  tps: number;
  tpot_ms: number;
  itl_avg_ms: number;
  total_tokens: number;
  total_time_ms: number;
}

interface ModelMetrics {
  [modelName: string]: PerformanceMetrics;
}

function App() {
  const [inputText, setInputText] = useState('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [modelLoading, setModelLoading] = useState(true);

  // 3つのウィンドウ用の状態
  const [selectedModel1, setSelectedModel1] = useState<string>('');
  const [selectedModel2, setSelectedModel2] = useState<string>('');

  const [outputs, setOutputs] = useState<ModelOutput>({});
  const [streamingOutputs, setStreamingOutputs] = useState<ModelOutput>({});
  const [isStreaming, setIsStreaming] = useState<StreamingState>({});
  const [metrics, setMetrics] = useState<ModelMetrics>({});
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 利用可能なOllamaモデルを取得
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/ollama/models`);
        const models = response.data.models || [];
        setAvailableModels(models);

        // 初期選択（利用可能な場合）
        if (models.length > 0) setSelectedModel1(models[0]);
        if (models.length > 1) setSelectedModel2(models[1]);

      } catch (err) {
        console.error('モデル一覧の取得に失敗しました:', err);
      } finally {
        setModelLoading(false);
      }
    };
    fetchModels();
  }, []);

  // ストリーミング生成を実行
  const handleGenerateStream = async () => {
    if (!inputText.trim()) {
      setError('入力テキストを入力してください');
      return;
    }

    const ollamaModelsToRequest = [selectedModel1, selectedModel2].filter(m => m !== '');

    setLoading(true);
    setError(null);
    setOutputs({});
    setStreamingOutputs({});
    setMetrics({});
    setEvaluation(null);

    // 各モデルのストリーミング状態を初期化
    const initialStreamingState: StreamingState = { 'OpenAI GPT-4.1': true };
    ollamaModelsToRequest.forEach(model => {
      initialStreamingState[model] = true;
    });
    setIsStreaming(initialStreamingState);

    // 前のリクエストをキャンセル
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_URL}/api/generate-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input_text: inputText,
          ollama_models: ollamaModelsToRequest
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      const currentOutputs: ModelOutput = {};

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const event = JSON.parse(dataStr);

              if (event.type === 'done') {
                // すべて完了
                setIsStreaming({});
                setLoading(false);

                // 評価を実行
                if (Object.keys(currentOutputs).length > 0) {
                  try {
                    const evalResponse = await axios.post(`${API_URL}/api/evaluate`, {
                      input_text: inputText,
                      outputs: currentOutputs
                    });
                    setEvaluation(evalResponse.data);
                  } catch (evalErr) {
                    console.error('評価エラー:', evalErr);
                  }
                }
                break;
              }

              if (event.type === 'partial') {
                // 部分出力を追加
                setStreamingOutputs(prev => ({
                  ...prev,
                  [event.model]: (prev[event.model] || '') + event.content
                }));
              } else if (event.type === 'complete') {
                // 完全な出力
                currentOutputs[event.model] = event.content;
                setOutputs(prev => ({
                  ...prev,
                  [event.model]: event.content
                }));
                setIsStreaming(prev => ({
                  ...prev,
                  [event.model]: false
                }));
                // メトリクスを保存
                if (event.metrics) {
                  setMetrics(prev => ({
                    ...prev,
                    [event.model]: event.metrics
                  }));
                }
              } else if (event.type === 'error') {
                setError(`${event.model}: ${event.content}`);
              }
            } catch (parseErr) {
              // JSON解析エラーは無視
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'ストリーミングエラーが発生しました');
        console.error('ストリーミングエラー:', err);
      }
    } finally {
      setLoading(false);
      setIsStreaming({});
    }
  };

  // ファイルアップロード処理
  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setInputText(response.data.content);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'ファイルアップロードに失敗しました');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileUpload(file);
  };

  // 出力表示用のヘルパー関数
  const getModelOutput = (modelName: string): string | null => {
    if (outputs[modelName]) return outputs[modelName];
    if (streamingOutputs[modelName]) return streamingOutputs[modelName];
    return null;
  };

  // メトリクス表示コンポーネント
  const MetricsPanel = ({ modelName }: { modelName: string }) => {
    const m = metrics[modelName];
    if (!m) return null;
    return (
      <div className="metrics-panel">
        <div className="metric-item">
          <span className="metric-label">TTFT</span>
          <span className="metric-value">{m.ttft_ms.toFixed(0)}<span className="metric-unit">ms</span></span>
        </div>
        <div className="metric-item">
          <span className="metric-label">TPS</span>
          <span className="metric-value">{m.tps.toFixed(1)}<span className="metric-unit">tok/s</span></span>
        </div>
        <div className="metric-item">
          <span className="metric-label">TPOT</span>
          <span className="metric-value">{m.tpot_ms.toFixed(1)}<span className="metric-unit">ms</span></span>
        </div>
        <div className="metric-item">
          <span className="metric-label">ITL</span>
          <span className="metric-value">{m.itl_avg_ms.toFixed(1)}<span className="metric-unit">ms</span></span>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>LLM MedGen Tool</h1>
        <p>複数のLLMによるデータ生成と評価ツール</p>
      </header>

      <main className="App-main">
        <section className="input-section">
          <h2>入力テキスト</h2>
          <div
            className={`file-drop-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <textarea
              className="input-textarea"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="ここに入力テキストを入力してください...&#10;（ファイルをドラッグ＆ドロップでも読み込めます）"
              rows={4}
            />
          </div>
          <div className="action-area">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".txt,.md,.csv"
              style={{ display: 'none' }}
            />
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              📄 ファイルを選択
            </button>
            <button
              className="generate-button"
              onClick={handleGenerateStream}
              disabled={loading || !inputText.trim()}
            >
              {loading ? '生成中...' : '全ウィンドウで生成を実行'}
            </button>
          </div>
        </section>

        {error && (
          <section className="error-section">
            <div className="error-message">{error}</div>
          </section>
        )}

        <section className="windows-section">
          {/* Window 1: OpenAI GPT-4.1 (Fixed) */}
          <div className="model-window">
            <div className="window-header">
              <h3>OpenAI GPT-4.1</h3>
              <span className="badge">Cloud</span>
            </div>
            <div className="window-content">
              {(() => {
                const output = getModelOutput("OpenAI GPT-4.1");
                if (output) {
                  return (
                    <>
                      {output}
                      {isStreaming["OpenAI GPT-4.1"] && <span className="cursor-blink">▊</span>}
                    </>
                  );
                }
                if (loading) return <div className="spinner">Generating...</div>;
                return <span className="placeholder">出力待機中...</span>;
              })()}
            </div>
            <MetricsPanel modelName="OpenAI GPT-4.1" />
          </div>

          {/* Window 2: Local Model 1 */}
          <div className="model-window">
            <div className="window-header">
              <select
                value={selectedModel1}
                onChange={(e) => setSelectedModel1(e.target.value)}
                disabled={modelLoading || loading}
              >
                <option value="">モデルを選択</option>
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <span className="badge local">Local</span>
            </div>
            <div className="window-content">
              {(() => {
                if (modelLoading) return <div className="spinner">Loading list...</div>;
                if (!selectedModel1) return <span className="placeholder">モデルを選択してください</span>;
                const output = getModelOutput(selectedModel1);
                if (output) {
                  return (
                    <>
                      {output}
                      {isStreaming[selectedModel1] && <span className="cursor-blink">▊</span>}
                    </>
                  );
                }
                if (loading) return <div className="spinner">Generating...</div>;
                return <span className="placeholder">出力待機中...</span>;
              })()}
            </div>
            <MetricsPanel modelName={selectedModel1} />
          </div>

          {/* Window 3: Local Model 2 */}
          <div className="model-window">
            <div className="window-header">
              <select
                value={selectedModel2}
                onChange={(e) => setSelectedModel2(e.target.value)}
                disabled={modelLoading || loading}
              >
                <option value="">モデルを選択</option>
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <span className="badge local">Local</span>
            </div>
            <div className="window-content">
              {(() => {
                if (modelLoading) return <div className="spinner">Loading list...</div>;
                if (!selectedModel2) return <span className="placeholder">モデルを選択してください</span>;
                const output = getModelOutput(selectedModel2);
                if (output) {
                  return (
                    <>
                      {output}
                      {isStreaming[selectedModel2] && <span className="cursor-blink">▊</span>}
                    </>
                  );
                }
                if (loading) return <div className="spinner">Generating...</div>;
                return <span className="placeholder">出力待機中...</span>;
              })()}
            </div>
            <MetricsPanel modelName={selectedModel2} />
          </div>
        </section>

        {evaluation && (
          <section className="evaluation-section">
            <h2>評価結果 (GPT-4による分析)</h2>
            <div className="evaluation-card">
              <div className="evaluation-content">
                <pre>{evaluation.evaluation}</pre>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;

