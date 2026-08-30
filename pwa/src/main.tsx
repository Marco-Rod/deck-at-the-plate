import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { App } from './app/App'
import { Providers } from './app/providers'

const container = document.getElementById('root')

if (!container) {
  throw new Error('Elemento raíz #root no encontrado')
}

createRoot(container).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
)
