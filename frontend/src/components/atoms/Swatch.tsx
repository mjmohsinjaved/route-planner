import Box from '@mui/material/Box'

export interface SwatchProps {
  color: string
  width: number | Record<string, number>
}

/** A short colored bar, used in the legend. */
export function Swatch({ color, width }: SwatchProps) {
  return <Box sx={{ width, height: 6, borderRadius: 3, bgcolor: color, flexShrink: 0 }} />
}
