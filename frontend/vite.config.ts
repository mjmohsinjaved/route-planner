import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: {
    // maplibre-gl alone is ~1 MB minified; it is one library in one lazy chunk and cannot be split further
    chunkSizeWarningLimit: 1100,
    // Vendor code in its own long-cached chunks, so an app change does not re-download
    // MapLibre (the largest dependency, also lazy-loaded by PlannerPage) or MUI.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'maplibre', test: /node_modules[\\/]maplibre-gl[\\/]/ },
            { name: 'mui', test: /node_modules[\\/](@mui|@emotion)[\\/]/ },
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
          ],
        },
      },
    },
  },
})
