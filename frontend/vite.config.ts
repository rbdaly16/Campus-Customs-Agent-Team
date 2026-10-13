import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The board calls the FastAPI backend directly at VITE_API_URL (default http://localhost:8000);
// the backend's CORS settings allow this dev origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
