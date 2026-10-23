import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'

import { FieldLabel } from '../atoms'
import type { TripRequest } from '../../types'

export type IntervalMiles = TripRequest['interval_mi']

const INTERVALS: IntervalMiles[] = [10, 25, 50]

export interface IntervalToggleProps {
  value: IntervalMiles
  onChange: (value: IntervalMiles) => void
}

/** Checkpoint interval picker: 10, 25 or 50 miles. */
export function IntervalToggle({ value, onChange }: IntervalToggleProps) {
  return (
    <div>
      <FieldLabel>Check weather every</FieldLabel>
      <ToggleButtonGroup
        exclusive
        fullWidth
        size="small"
        color="primary"
        value={value}
        onChange={(_, next: IntervalMiles | null) => next && onChange(next)}
        aria-label="Checkpoint interval"
      >
        {INTERVALS.map((miles) => (
          <ToggleButton key={miles} value={miles}>
            {miles} mi
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </div>
  )
}
