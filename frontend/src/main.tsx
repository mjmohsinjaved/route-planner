import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import CssBaseline from '@mui/material/CssBaseline'
import GlobalStyles from '@mui/material/GlobalStyles'
import { ThemeProvider } from '@mui/material/styles'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import PlannerPage from './components/pages/PlannerPage'
import { theme } from './theme'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {/* Theme values that plain CSS (index.css) needs beyond what MUI emits on its own */}
        <GlobalStyles styles={(t) => ({ ':root': { '--font-sans': t.typography.fontFamily } })} />
        <PlannerPage />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
