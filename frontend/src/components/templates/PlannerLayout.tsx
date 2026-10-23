import type { ReactNode } from 'react'

import Box from '@mui/material/Box'
import LinearProgress from '@mui/material/LinearProgress'
import Paper from '@mui/material/Paper'

export interface PlannerLayoutProps {
  sidebar: ReactNode
  map: ReactNode
  isLoading?: boolean
}

// Narrower on a tablet (768 px, theme `md`) so the map keeps more than half the width
const SIDEBAR_WIDTH = { md: 340, lg: 400 }

/** Sidebar beside the map on tablets and up; map above the sidebar on phones. */
export function PlannerLayout({ sidebar, map, isLoading = false }: PlannerLayoutProps) {
  return (
    <Box
      component="main"
      sx={{
        height: '100dvh',
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: `${SIDEBAR_WIDTH.md}px 1fr`, lg: `${SIDEBAR_WIDTH.lg}px 1fr` },
        gridTemplateRows: { xs: '50dvh 1fr', md: '1fr' },
        bgcolor: 'background.default',
      }}
    >
      <Paper
        component="aside"
        square
        elevation={0}
        sx={{
          order: { xs: 2, md: 1 },
          borderRight: { md: 1 },
          borderColor: { md: 'divider' },
          overflowY: 'auto',
          position: 'relative',
        }}
      >
        {isLoading && <LinearProgress sx={{ position: 'sticky', top: 0, zIndex: 2 }} />}
        <Box sx={{ p: 2.5 }}>{sidebar}</Box>
      </Paper>

      <Box sx={{ order: { xs: 1, md: 2 }, minHeight: 0, position: 'relative' }}>{map}</Box>
    </Box>
  )
}
