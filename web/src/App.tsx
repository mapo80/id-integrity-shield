// web/src/App.tsx
import React, { useMemo, useState } from "react";
import { Upload, Typography, Button, Card, Space, Image, Alert, Spin, Progress, message } from "antd";
import { InboxOutlined, CheckCircleTwoTone, CloudUploadOutlined, DeleteOutlined } from "@ant-design/icons";
import AnalysisView from "./components/AnalysisView";
import type { SdkReport } from "./types";
import { analyzeImage } from "./api";

const { Dragger } = Upload;
const { Title, Text } = Typography;

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadPct, setUploadPct] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<SdkReport | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);
  const profile = import.meta.env.VITE_DEFAULT_PROFILE || "recapture-id@2";

  const props = {
    name: "file",
    multiple: false,
    showUploadList: false,
    beforeUpload: () => false, // evita upload automatico di antd — gestiamo noi
    onDrop: () => {},
    onChange(info: any) {
      setErr(null);
      setResp(null);
      const f = info.file as File;
      if (!f) return;
      setFile(f);
      message.success(`File selezionato: ${f.name}`);
    },
    onDragOver() {
      setDragActive(true);
    },
    onDragLeave() {
      setDragActive(false);
    },
  };

  async function analyze() {
    if (!file) return;
    try {
      setLoading(true);
      setUploadPct(15); // feedback immediato
      setErr(null);
      setResp(null);

      const progTimer = setInterval(() => {
        setUploadPct((p) => (p < 90 ? p + 5 : p));
      }, 150);

      const data = await analyzeImage(file, { profile }).finally(() => {
        clearInterval(progTimer);
      });

      setUploadPct(100);
      setResp(data);
    } catch (e: any) {
      setErr(e?.message ?? "Errore sconosciuto");
    } finally {
      setLoading(false);
      setTimeout(() => setUploadPct(0), 500);
    }
  }

  function reset() {
    setFile(null);
    setResp(null);
    setErr(null);
    setUploadPct(0);
    setDragActive(false);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0b1220", padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <div style={{ textAlign: "center" }}>
            <Title style={{ color: "white", marginBottom: 8 }}>ID Integrity Shield — Demo</Title>
            <Text style={{ color: "rgba(255,255,255,0.75)" }}>
              Trascina un’immagine qui sotto e premi <b>Analizza</b>. Il profilo è <code style={{ color: "#b5f5ec" }}>{profile}</code>.
            </Text>
          </div>

          {/* DROPZONE */}
          <Card
            style={{
              borderRadius: 16,
              borderColor: dragActive ? "#69b1ff" : "rgba(255,255,255,0.1)",
              background: dragActive ? "rgba(105,177,255,0.08)" : "rgba(255,255,255,0.04)",
              transition: "all .2s ease",
            }}
            bodyStyle={{ padding: 0 }}
          >
            <Dragger
              {...props}
              style={{
                padding: 28,
                borderRadius: 16,
                background: "transparent",
                border: "1px dashed rgba(255,255,255,0.2)",
              }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ color: "#69b1ff" }} />
              </p>
              <p className="ant-upload-text" style={{ color: "white" }}>
                Trascina qui il file oppure <span style={{ color: "#69b1ff" }}>clicca per selezionarlo</span>
              </p>
              <p className="ant-upload-hint" style={{ color: "rgba(255,255,255,0.65)" }}>
                Formati supportati: JPG/PNG. Un solo file alla volta.
              </p>
            </Dragger>

            {/* Barra di stato file selezionato */}
            <div
              style={{
                padding: file ? 16 : 0,
                display: file ? "block" : "none",
                borderTop: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <Space align="center" style={{ width: "100%", justifyContent: "space-between" }}>
                <Space size="middle" align="center">
                  <CheckCircleTwoTone twoToneColor="#52c41a" />
                  <Text style={{ color: "white" }}>
                    File selezionato: <b>{file?.name}</b>{" "}
                    <span style={{ color: "rgba(255,255,255,0.6)" }}>({Math.round((file?.size || 0) / 1024)} KB)</span>
                  </Text>
                </Space>
                <Space>
                  <Button icon={<DeleteOutlined />} onClick={reset}>
                    Rimuovi
                  </Button>
                  <Button
                    type="primary"
                    icon={<CloudUploadOutlined />}
                    disabled={!file || loading}
                    loading={loading}
                    onClick={analyze}
                  >
                    Analizza
                  </Button>
                </Space>
              </Space>

              {/* Preview + progress */}
              <div style={{ marginTop: 12, display: "flex", gap: 16, alignItems: "center" }}>
                <Image
                  src={previewUrl}
                  alt="preview"
                  width={120}
                  height={120}
                  style={{ objectFit: "cover", borderRadius: 8 }}
                  placeholder
                />
                <div style={{ flex: 1 }}>
                  {loading ? (
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <Spin />
                      <Text style={{ color: "rgba(255,255,255,0.85)" }}>Analisi in corso…</Text>
                    </div>
                  ) : (
                    <Text style={{ color: "rgba(255,255,255,0.65)" }}>
                      Pronto all’analisi. Clicca <b>Analizza</b>.
                    </Text>
                  )}
                  {uploadPct > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Progress percent={uploadPct} size="small" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Errori */}
          {err && (
            <Alert
              type="error"
              showIcon
              message="Errore durante l’analisi"
              description={<pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{err}</pre>}
            />
          )}

            {/* Risultato */}
            {resp && <AnalysisView fileUrl={previewUrl} report={resp} />}
        </Space>
      </div>
    </div>
  );
}
