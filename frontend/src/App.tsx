import { useState, useEffect, useCallback } from 'react'
import { Toaster } from 'react-hot-toast'
import axios from 'axios'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import DocumentPreviewer from './components/DocumentPreviewer'
import { API_BASE_URL } from './config'

const API_BASE = API_BASE_URL

interface DocItem {
  id: string
  name: string
}

function App() {
  const [currentDoc, setCurrentDoc] = useState<string | null>(null)
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [docs, setDocs] = useState<DocItem[]>([])
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const fetchDocs = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/docs`, { timeout: 5000 })
      setDocs(response.data.map((d: any) => ({ id: d.id, name: d.name })))
    } catch { /* silent */ }
  }, [])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const handleConversationChange = useCallback((id: string | null) => {
    setConversationId(id)
    setRefreshTrigger(prev => prev + 1)
  }, [])

  const handlePreview = useCallback((docId: string) => {
    setPreviewDocId(docId)
  }, [])

  const handleClosePreview = useCallback(() => {
    setPreviewDocId(null)
  }, [])

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
      <div className="flex h-screen bg-gray-50">
        <Sidebar
          currentDoc={currentDoc}
          onSelectDoc={setCurrentDoc}
          currentConversation={conversationId}
          onSelectConversation={handleConversationChange}
          refreshTrigger={refreshTrigger}
          onPreview={handlePreview}
        />
        <ChatArea
          currentDoc={currentDoc}
          conversationId={conversationId}
          onConversationChange={handleConversationChange}
          docs={docs}
          onPreview={handlePreview}
        />
        {previewDocId && (
          <DocumentPreviewer docId={previewDocId} onClose={handleClosePreview} />
        )}
      </div>
    </>
  )
}

export default App
