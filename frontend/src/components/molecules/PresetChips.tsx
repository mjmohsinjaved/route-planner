import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'

import { TRIP_PRESETS, type TripPreset } from '../../constants/trip-presets'
import { FieldLabel } from '../atoms'

export interface PresetChipsProps {
  onPick: (preset: TripPreset) => void
}

/** Example trips as one-click chips. */
export function PresetChips({ onPick }: PresetChipsProps) {
  return (
    <div>
      <FieldLabel>Try an example</FieldLabel>
      <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: 'wrap' }}>
        {TRIP_PRESETS.map((preset) => (
          <Chip key={preset.label} label={preset.label} size="small" variant="outlined" onClick={() => onPick(preset)} />
        ))}
      </Stack>
    </div>
  )
}
