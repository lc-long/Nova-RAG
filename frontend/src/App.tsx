import { Toaster } from 'react-hot-toast'
import { useDocuments } from './hooks/useDocuments'
import { useConversations } from './hooks/useConversations'
import { useAppStore } from './store/useAppStore'
import { useTheme } from './contexts/ThemeContext'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentPreviewer from './components/DocumentPreviewer'
import { ErrorBoundary } from './components/ErrorBoundary'

function App() {
  const docs = useAppStore((s) => s.docs)
  const { previewDocId, handleClosePreview, handlePreview } = useDocuments()
  const { loadConversations } = useConversations()
  const { resolvedTheme } = useTheme()

  const handleConversationChange = () => {
    loadConversations()
  }

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: resolvedTheme === 'dark' ? '#1e2235' : '#ffffff',
            color: resolvedTheme === 'dark' ? '#f1f5f9' : '#0f172a',
            border: resolvedTheme === 'dark' ? '1px solid #2d3348' : '1px solid #e2e8f0',
            boxShadow: '0 4px 12px -2px rgb(0 0 0 / 0.15)',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: resolvedTheme === 'dark' ? '#052e16' : '#f0fdf4',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: resolvedTheme === 'dark' ? '#1c0a0a' : '#fef2f2',
            },
          },
        }}
      />
      <div className="flex h-screen bg-[var(--color-bg-primary)] relative transition-colors duration-200">
        <Sidebar onConversationChange={handleConversationChange} />
        <ChatArea docs={docs} onPreview={handlePreview} />
        {previewDocId && (
          <div className="absolute top-0 right-0 h-full w-[45%] min-w-[360px] max-w-[640px] z-30
                        shadow-[-8px_0_24px_-4px_rgb(0_0_0_/_0.1)]">
            <DocumentPreviewer docId={previewDocId} onClose={handleClosePreview} />
          </div>
        )}
      </div>
    </>
  )
}

export default function AppWithBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}