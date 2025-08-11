import type { SdkReport } from './types'

export function verdictFromReport(rep: SdkReport): {verdict: 'TAMPERED'|'CLEAN'|'UNKNOWN', threshold?: number} {
  if (typeof rep.decision === 'boolean') {
    return { verdict: rep.decision ? 'TAMPERED' : 'CLEAN' }
  }
  const thr = rep.decision?.threshold ?? rep.threshold
  if (typeof rep.tamper_score === 'number' && typeof thr === 'number') {
    return { verdict: rep.tamper_score >= thr ? 'TAMPERED' : 'CLEAN', threshold: thr }
  }
  return { verdict: 'UNKNOWN' }
}

export function summarize(rep: SdkReport): string {
  const lines: string[] = []
  const v = verdictFromReport(rep)
  const score = rep.tamper_score
  const conf = rep.confidence
  const prof = rep.profile_id || 'profilo sconosciuto'
  lines.push(`Analisi completata con il profilo ${prof}.`)
  if (typeof score === 'number') {
    const thr = v.threshold != null ? ` (soglia ${v.threshold.toFixed(2)})` : ''
    lines.push(`Tamper score: ${score.toFixed(3)}${thr} ⇒ verdetto: ${v.verdict}.`)
  }
  if (typeof conf === 'number') lines.push(`Confidenza del verdetto: ${Math.round(conf*100)}% (0%=incerto, 100%=massima).`)
  if (v.verdict === 'UNKNOWN') lines.push('Il verdetto è UNKNOWN perché mancano score o soglia.')

  if (rep.checks && Object.keys(rep.checks).length) {
    const items = Object.entries(rep.checks).map(([name, c]) => {
      const s = c?.score != null ? c.score.toFixed(3) : 'n/d'
      const t = c?.threshold != null ? c.threshold.toFixed(2) : 'n/d'
      const w = c?.weight != null ? c.weight.toFixed(2) : 'n/d'
      const dec = c?.decision != null ? String(c.decision) : 'n/d'
      return `• ${name}: score ${s}, soglia ${t}, peso ${w}, decisione ${dec}`
    })
    lines.push('Dettaglio controlli:')
    lines.push(...items)
  } else {
    lines.push('Nessun controllo eseguito.')
  }

  const hms: string[] = []
  if (rep.artifacts) {
    for (const [k, v] of Object.entries(rep.artifacts)) {
      if (/heatmap|overlay/i.test(k) || /\.png$|\.jpg$/i.test(v)) {
        hms.push(k)
      }
    }
  }
  if (hms.length) {
    lines.push(`Sono disponibili heatmap/overlay: ${hms.join(', ')}.`)
  }
  return lines.join('\n')
}
