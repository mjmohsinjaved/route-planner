import Box from '@mui/material/Box'
import Tooltip from '@mui/material/Tooltip'

import { RISK_COLORS, RISK_LEVELS } from '../../theme/risk'
import type { Checkpoint } from '../../types'

export interface RiskBarProps {
  checkpoints: Checkpoint[]
}

/** Miles at each risk level as one stacked bar. */
export function RiskBar({ checkpoints }: RiskBarProps) {
  const miles = RISK_LEVELS.map(() => 0)
  for (const c of checkpoints) miles[c.level_score] += c.segment_mi
  const total = miles.reduce((a, b) => a + b, 0) || 1

  return (
    <Box sx={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', bgcolor: 'divider' }}>
      {RISK_LEVELS.map((level, i) =>
        miles[i] > 0 ? (
          <Tooltip key={level} title={`${level}: ${Math.round(miles[i])} mi`} arrow>
            <Box sx={{ width: `${(miles[i] / total) * 100}%`, bgcolor: RISK_COLORS[level] }} />
          </Tooltip>
        ) : null,
      )}
    </Box>
  )
}
