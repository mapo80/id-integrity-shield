import React, { useMemo, useState } from 'react'
import { Layout, ConfigProvider, theme, Row, Col, Card, Form, Input, Button, Space, Spin, Alert } from 'antd'
import { CloudUploadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import UploadArea from './components/UploadArea'
import AnalysisView from './components/AnalysisView'
import { analyzeImage } from './api'
import type { SdkReport } from './types'

const { Header, Content, Footer } = Layout

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [fileUrl, setFileUrl] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [report, setReport] = useState<SdkReport | null>(null)
  const [profile, setProfile] = useState<string>(import.meta.env.VITE_DEFAULT_PROFILE || 'recapture-id@2')
  const [paramsJson, setParamsJson] = useState<string>('')

  const themeCfg = useMemo(() => ({
    algorithm: theme.darkAlgorithm,
    token: { colorBgBase: '#0b1220', colorText: '#dbe6ff' }
  }), [])

  async function onAnalyze() {
    if (!file) return
    setError('')
    setReport(null)
    setLoading(true)
    try {
      const rep = await analyzeImage(file, { profile, paramsJson })
      setReport(rep)
    } catch (e:any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <ConfigProvider theme={themeCfg}>
      <Layout className="app">
        <Header className="header">
          <div className="brand">ID Integrity Shield — Viewer</div>
          <div className="sub">Carica una sola immagine, avvia l'analisi e visualizza il verdetto, i dettagli dei controlli e le heatmap.</div>
        </Header>
        <Content style={{ padding: 24 }}>
          <Row gutter={[16,16]}>
            <Col xs={24} lg={10}>
              <Card className="card" title="Input">
                <Space direction="vertical" style={{width:'100%'}} size={16}>
                  <UploadArea onFile={(f) => { setFile(f); setFileUrl(URL.createObjectURL(f)) }} />
                  <Form layout="vertical">
                    <Form.Item label="Profilo">
                      <Input placeholder="es. recapture-id@2" value={profile} onChange={e => setProfile(e.target.value)} />
                    </Form.Item>
                    <Form.Item label="Params (JSON opzionale)">
                      <Input.TextArea autoSize={{minRows:3, maxRows:6}} placeholder='{"noiseprintpp":{"model_path":"..."}}' value={paramsJson} onChange={e => setParamsJson(e.target.value)} />
                    </Form.Item>
                    <Space>
                      <Button type="primary" icon={<ThunderboltOutlined />} disabled={!file} onClick={onAnalyze}>Analizza</Button>
                      <Button icon={<CloudUploadOutlined />} disabled={!file} onClick={() => { setFile(null); setReport(null); setFileUrl('') }}>Reset</Button>
                    </Space>
                  </Form>
                  {error && <Alert type="error" showIcon message="Errore" description={error} />}
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={14}>
              <Spin spinning={loading} tip="Analisi in corso...">
                {report ? (
                  <AnalysisView fileUrl={fileUrl} report={report} />
                ) : (
                  <Card className="card"><div style={{color:'#9fb1d1'}}>Nessun risultato ancora. Carica un'immagine e premi <b>Analizza</b>.</div></Card>
                )}
              </Spin>
            </Col>
          </Row>
        </Content>
        <Footer className="footer">
          Imposta <code>VITE_API_BASE_URL</code> e <code>VITE_API_KEY</code> nel tuo <code>.env</code> per puntare all'API dello SDK.
        </Footer>
      </Layout>
    </ConfigProvider>
  )
}
