import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'

function App() {
  const [currentDoc, setCurrentDoc] = useState<string | null>(null)

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
        <Sidebar currentDoc={currentDoc} onSelectDoc={setCurrentDoc} />
        <ChatArea />
      </div>
    </>
  )
}

export default App