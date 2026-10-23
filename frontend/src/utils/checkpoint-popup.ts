import { RISK_COLORS } from '../theme/risk'
import { formatDateTime } from './format'
import type { Checkpoint } from '../types'

const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

/** HTML for the MapLibre popup on a checkpoint. Styled by the `.cp-*` rules in index.css. */
export function checkpointPopupHtml(c: Checkpoint): string {
  const color = RISK_COLORS[c.level]
  const gusts = c.gust_mph == null ? '' : ` <span class="cp-muted">(gusts ${c.gust_mph.toFixed(0)})</span>`
  return `
    <div class="cp-popup">
      <div class="cp-head">
        <span class="cp-chip" style="background:${color}">${escapeHtml(c.level)}</span>
        <span>Mile ${Math.round(c.mile)}</span>
      </div>
      <div class="cp-eta">ETA ${escapeHtml(formatDateTime(c.eta))}</div>
      <table>
        <tr><td>Wind</td><td>${c.wind_mph.toFixed(1)} mph${gusts}</td></tr>
        <tr><td>Rain</td><td>${c.rain_in_hr.toFixed(2)} in/hr</td></tr>
        <tr><td>Snow</td><td>${c.snow_in_hr.toFixed(2)} in/hr</td></tr>
      </table>
      <div class="cp-reason">${escapeHtml(c.reason)}</div>
    </div>`
}
