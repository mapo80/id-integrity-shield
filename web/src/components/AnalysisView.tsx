import React from 'react'
import type { SdkReport } from '../types'
import { Card, Descriptions, Progress, Tag, Tabs, Image, Typography, Space, Table } from 'antd'
import { resolveArtifactUrl } from '../api'
import { verdictFromReport, summarize } from '../utils'

type Props = { fileUrl: string; report: SdkReport }

function CheckTag({ ok }: { ok: boolean | undefined }) {
  if (ok === undefined) return <Tag>n/d</Tag>
  return ok ? <Tag color="red">sospetto</Tag> : <Tag color="green">ok</Tag>
}

export default function AnalysisView({ fileUrl, report }: Props) {
  const v = verdictFromReport(report)
  const checks = Object.entries(report.checks || {})
  const columns = [
    { title: 'Check', dataIndex: 'name', key: 'name' },
    { title: 'Score', dataIndex: 'score', key: 'score', render: (v:number|undefined) => v!=null ? v.toFixed(3) : 'n/d' },
    { title: 'Soglia', dataIndex: 'threshold', key: 'threshold', render: (v:number|undefined) => v!=null ? v.toFixed(2) : 'n/d' },
    { title: 'Peso', dataIndex: 'weight', key: 'weight', render: (v:number|undefined) => v!=null ? v.toFixed(2) : 'n/d' },
    { title: 'Esito', dataIndex: 'decision', key: 'decision', render: (d:boolean|undefined) => <CheckTag ok={d}/> },
  ]
  const data = checks.map(([name, c]) => ({ key: name, name, score: c?.score, threshold: c?.threshold, weight: c?.weight, decision: c?.decision }))

  const globalArtifacts: string[] = []
  if (report.artifacts) {
    for (const [, v] of Object.entries(report.artifacts)) {
      if (typeof v === 'string') globalArtifacts.push(resolveArtifactUrl(v))
    }
  }
  const heatmaps: Array<{label:string,url:string}> = []
  checks.forEach(([name, c]) => {
    const arts = (c?.artifacts || {}) as Record<string,string>
    Object.entries(arts).forEach(([k, v]) => {
      if (/heatmap|overlay|mask/i.test(k)) heatmaps.push({ label: `${name}:${k}`, url: resolveArtifactUrl(v) })
    })
  })

  const narrative = summarize(report)

  return (
    <Space direction="vertical" size={16} style={{ width:'100%' }}>
      <Card className="card" title={<Typography.Text style={{color:'white'}}>Verdetto</Typography.Text>}>
        <Space direction="vertical" size={12} style={{ width:'100%' }}>
          <Space align="center" wrap>
            <Typography.Title level={3} style={{color:'white', margin:0}}>
              {v.verdict === 'TAMPERED' ? 'TAMPERED' : v.verdict === 'CLEAN' ? 'CLEAN' : 'Sconosciuto'}
            </Typography.Title>
            {typeof report.tamper_score === 'number' &&
              <Progress percent={Math.round(report.tamper_score*100)} steps={12} showInfo format={() => `score ${report.tamper_score?.toFixed(3)}`} />}
          </Space>
          <Descriptions bordered column={2} size="small" style={{ background:'transparent' }}
            items={[
              { key:'prof', label:'Profilo', children: report.profile_id || 'n/d' },
              { key:'thr', label:'Soglia', children: v.threshold != null ? v.threshold.toFixed(2) : 'n/d' },
              { key:'conf', label:'Confidenza', children: report.confidence != null ? `${Math.round((report.confidence||0)*100)}%` : 'n/d' },
              { key:'version', label:'Versione', children: (report.version || report.runtime?.git || 'n/d') }
            ]}
          />
        </Space>
      </Card>

      <Card className="card" title={<Typography.Text style={{color:'white'}}>Confronto visivo</Typography.Text>}>
        <Tabs
          items={[
            { key:'orig', label:'Originale', children: <Image src={fileUrl} alt="originale" /> },
            ...heatmaps.length ? [{ key:'hm', label:`Heatmap/Overlay (${heatmaps.length})`, children: (
                <Image.PreviewGroup>
                  <Space size={[12,12]} wrap>
                    {heatmaps.map((h, i) => <Image key={i} width={360} src={h.url} alt={h.label} />)}
                    {globalArtifacts.map((u, i) => <Image key={'g'+i} width={360} src={u} alt={'artifact '+i} />)}
                  </Space>
                </Image.PreviewGroup>
            ) }] : []
          ]}
        />
      </Card>

      <Card className="card" title={<Typography.Text style={{color:'white'}}>Dettaglio controlli</Typography.Text>}>
        <Table columns={columns} dataSource={data} pagination={false} />
      </Card>

      <Card className="card" title={<Typography.Text style={{color:'white'}}>Descrizione testuale</Typography.Text>}>
        <Typography.Paragraph style={{whiteSpace:'pre-wrap', color:'white'}}>{narrative}</Typography.Paragraph>
      </Card>
    </Space>
  )
}
