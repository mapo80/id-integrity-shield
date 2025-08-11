import React from 'react'
import type { SdkReport } from '../types'
import { Card, Descriptions, Progress, Tag, Tabs, Image, Typography, Space, Table, Tooltip } from 'antd'
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

   const CHECK_DESCRIPTIONS: Record<string, string> = {
     mantranet: 'Rete neurale che evidenzia manipolazioni pixel-level',
     noiseprintpp: 'Analisi della firma di rumore della fotocamera',
     jpeg_ghost: 'Rileva ricompressioni JPEG differenti',
     ela: 'Error Level Analysis: evidenzia aree ricampionate',
     blockiness: 'Controllo discontinuità dei blocchi JPEG',
     copy_move: 'Ricerca regioni duplicate (copy-move)',
     splicing: 'Analizza incoerenze tra porzioni incollate',
     noise: 'Valuta incoerenze di rumore',
     exif: 'Verifica coerenza dei metadati EXIF',
   }

   const ARTIFACT_DESCRIPTIONS: Record<string, string> = {
     heatmap: 'Heatmap: intensità del sospetto (rosso=alto)',
     overlay: "Overlay: aree sospette sovrapposte all'originale",
     fused_heatmap: 'Heatmap fusa di tutti i controlli',
     mask: 'Maschera binaria delle zone sospette',
   }

   const columns = [
     {
       title: 'Check',
       dataIndex: 'name',
       key: 'name',
       render: (n: string) => (
         <Tooltip title={CHECK_DESCRIPTIONS[n] || 'n/d'}>
           <span>{n}</span>
         </Tooltip>
       ),
     },
     { title: 'Score', dataIndex: 'score', key: 'score', render: (v:number|undefined) => v!=null ? v.toFixed(3) : 'n/d' },
     { title: 'Soglia', dataIndex: 'threshold', key: 'threshold', render: (v:number|undefined) => v!=null ? v.toFixed(2) : 'n/d' },
     { title: 'Peso', dataIndex: 'weight', key: 'weight', render: (v:number|undefined) => v!=null ? v.toFixed(2) : 'n/d' },
     { title: 'Contributo', dataIndex: 'contribution', key: 'contribution', render: (v:number|undefined) => v!=null ? v.toFixed(3) : 'n/d' },
     { title: 'Esito', dataIndex: 'decision', key: 'decision', render: (d:boolean|undefined) => <CheckTag ok={d}/> },
     { title: 'Descrizione', dataIndex: 'description', key: 'description' },
   ]

   const data = checks.map(([name, c]) => {
     const score = c?.score ?? 0
     const weight = c?.weight ?? 0
     return {
       key: name,
       name,
       score: c?.score,
       threshold: c?.threshold,
       weight: c?.weight,
       contribution: score * weight,
       decision: c?.decision,
       description: CHECK_DESCRIPTIONS[name] || '-',
     }
   })

   const artifacts: Array<{ label: string; url: string; isImage: boolean; type: string }> = []
   const artifactKeys = new Set<string>()

   if (report.artifacts) {
     for (const [k, v] of Object.entries(report.artifacts)) {
       if (typeof v === 'string') {
         const url = resolveArtifactUrl(v)
         const isImage = /\.png$|\.jpg$|\.jpeg$|\.gif$|\.webp$/i.test(v)
         artifacts.push({ label: `global:${k}`, url, isImage, type: k })
         artifactKeys.add(k)
       }
     }
   }

   checks.forEach(([name, c]) => {
     const arts = (c?.artifacts || {}) as Record<string, string>
     Object.entries(arts).forEach(([k, v]) => {
       if (typeof v === 'string') {
         const url = resolveArtifactUrl(v)
         const isImage = /\.png$|\.jpg$|\.jpeg$|\.gif$|\.webp$/i.test(v)
         artifacts.push({ label: `${name}:${k}`, url, isImage, type: k })
         artifactKeys.add(k)
       }
     })
   })

   const imageArtifacts = artifacts.filter(a => a.isImage)
   const otherArtifacts = artifacts.filter(a => !a.isImage)

   const narrative = summarize(report)

   const weightSum = data.reduce((s, d) => s + (d.weight ?? 0), 0)
   const weighted = data.reduce((s, d) => s + (d.contribution ?? 0), 0)
   const calcScore = weightSum ? weighted / weightSum : undefined

   const legendItems = Array.from(artifactKeys).map(k => ({
     key: k,
     label: k,
     children: ARTIFACT_DESCRIPTIONS[k] || '-',
   }))

   return (
     <Space direction="vertical" size={16} style={{ width: '100%' }}>
       <Card className="card" title={<Typography.Text style={{ color: 'white' }}>Verdetto</Typography.Text>}>
         <Space direction="vertical" size={12} style={{ width: '100%' }}>
           <Space align="center" wrap>
             <Typography.Title level={3} style={{ color: 'white', margin: 0 }}>
               {v.verdict === 'TAMPERED' ? 'TAMPERED' : v.verdict === 'CLEAN' ? 'CLEAN' : 'Sconosciuto'}
             </Typography.Title>
             {typeof report.tamper_score === 'number' && (
               <Progress
                 percent={Math.round(report.tamper_score * 100)}
                 steps={12}
                 showInfo
                 format={() => `score ${report.tamper_score?.toFixed(3)}`}
               />
             )}
           </Space>
           <Descriptions
             bordered
             column={2}
             size="small"
             style={{ background: 'transparent' }}
             items={[
               { key: 'prof', label: 'Profilo', children: report.profile_id || 'n/d' },
               { key: 'score', label: 'Score finale', children: report.tamper_score != null ? report.tamper_score.toFixed(3) : 'n/d' },
               { key: 'thr', label: 'Soglia', children: v.threshold != null ? v.threshold.toFixed(2) : 'n/d' },
               { key: 'conf', label: 'Confidenza', children: report.confidence != null ? `${Math.round((report.confidence||0)*100)}%` : 'n/d' },
               { key: 'version', label: 'Versione', children: report.version || report.runtime?.git || 'n/d' },
             ]}
           />
         </Space>
       </Card>

       <Card className="card" title={<Typography.Text style={{ color: 'white' }}>Confronto visivo</Typography.Text>}>
         <Tabs
           items={[
             { key: 'orig', label: 'Originale', children: <Image src={fileUrl} alt="originale" /> },
             ...artifacts.length
               ? [
                   {
                     key: 'art',
                     label: `Artefatti (${artifacts.length})`,
                     children: (
                       <Space direction="vertical" size={16} style={{ width: '100%' }}>
                         {imageArtifacts.length > 0 && (
                           <Image.PreviewGroup>
                             <Space size={[12, 12]} wrap>
                               {imageArtifacts.map((a, i) => (
                                 <div key={i} style={{ textAlign: 'center' }}>
                                   <Image width={360} src={a.url} alt={a.label} />
                                   <Typography.Text style={{ color: 'white' }}>{a.label}</Typography.Text>
                                 </div>
                               ))}
                             </Space>
                           </Image.PreviewGroup>
                         )}
                         {otherArtifacts.length > 0 && (
                           <Space direction="vertical" size={4}>
                             {otherArtifacts.map((a, i) => (
                               <Typography.Link key={i} href={a.url} target="_blank">
                                 {a.label}
                               </Typography.Link>
                             ))}
                           </Space>
                         )}
                         {legendItems.length > 0 && (
                           <Descriptions
                             size="small"
                             column={1}
                             style={{ background: 'transparent' }}
                             labelStyle={{ color: 'white' }}
                             contentStyle={{ color: 'white' }}
                             items={legendItems}
                           />
                         )}
                       </Space>
                     ),
                   },
                 ]
               : [],
           ]}
         />
       </Card>

       <Card className="card" title={<Typography.Text style={{ color: 'white' }}>Dettaglio controlli</Typography.Text>}>
         <Table columns={columns} dataSource={data} pagination={false} scroll={{ x: true }} />
         <Typography.Paragraph style={{ color: 'white', marginTop: 12 }}>
           Tamper score = Σ(score × peso) / Σ(pesi) = {calcScore != null ? calcScore.toFixed(3) : 'n/d'}
         </Typography.Paragraph>
       </Card>

       <Card className="card" title={<Typography.Text style={{ color: 'white' }}>Descrizione testuale</Typography.Text>}>
         <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', color: 'white' }}>{narrative}</Typography.Paragraph>
       </Card>
     </Space>
   )
 }
