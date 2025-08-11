import React from 'react'
import { Upload, Typography, theme } from 'antd'
import { InboxOutlined } from '@ant-design/icons'

type Props = { onFile: (file: File) => void }
const { Dragger } = Upload

export default function UploadArea({ onFile }: Props) {
  const { token } = theme.useToken()
  return (
    <Dragger
      multiple={false}
      accept="image/*"
      maxCount={1}
      beforeUpload={(file) => { onFile(file); return Upload.LIST_IGNORE }}
      showUploadList={false}
      style={{ padding: 24, borderRadius: 12, background: 'rgba(255,255,255,0.02)', border: '1px dashed ' + token.colorBorder }}
    >
      <p className="ant-upload-drag-icon"><InboxOutlined /></p>
      <Typography.Title level={4} style={{ color: 'white', marginBottom: 0 }}>Trascina qui una sola immagine</Typography.Title>
      <p className="drop-hint">Oppure clicca per selezionarla dal tuo computer</p>
    </Dragger>
  )
}
