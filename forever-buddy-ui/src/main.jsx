import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

const isAdmin = window.location.pathname.startsWith('/admin')

async function init() {
  if (isAdmin) {
    await import('./AdminPanel.css')
    const { default: AdminPanel } = await import('./AdminPanel.jsx')
    createRoot(document.getElementById('root')).render(
      <StrictMode><AdminPanel /></StrictMode>
    )
  } else {
    await import('./index.css')
    await import('./App.css')
    const { default: App } = await import('./App.jsx')
    createRoot(document.getElementById('root')).render(
      <StrictMode><App /></StrictMode>
    )
  }
}

init()