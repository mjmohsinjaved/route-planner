import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

export interface FieldLabelProps {
  children: ReactNode
  htmlFor?: string
  hasError?: boolean
}

/** Caption-sized label above a control that has no label of its own. */
export function FieldLabel({ children, htmlFor, hasError = false }: FieldLabelProps) {
  return (
    <Typography
      component={htmlFor ? 'label' : 'div'}
      htmlFor={htmlFor}
      variant="caption"
      color={hasError ? 'error' : 'text.secondary'}
      sx={{ display: 'block', mb: 0.5 }}
    >
      {children}
    </Typography>
  )
}
