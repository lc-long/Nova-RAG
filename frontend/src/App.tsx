import { Toaster } from 'react-hot-toast'
import { useDocuments } from './hooks/useDocuments'
import { useConversations } from './hooks/useConversations'
import { useAppStore } from './store/useAppStore'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentPreviewer from './components/DocumentPreviewer'
import { ErrorBoundary } from './components/ErrorBoundary'

function App() {
  const docs = useAppStore((s) => s.docs)
  const {
    previewDocId, handleClosePreview, handlePreview,
  } = useDocuments()
  const { loadConversations } = useConversations()

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
            background: '#EF4444',
            color: '#fff',
            fontWeight: 500,
          },
        }}
      />
      <div className="flex h-screen bg-gray-50 relative">
        <Sidebar onConversationChange={handleConversationChange} />
        <ChatArea docs={docs} onPreview={handlePreview} />
        {previewDocId && (
          <div className="absolute top-0 right-0 h-full w-[45%] min-w-[360px] max-w-[640px] z-30">
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
