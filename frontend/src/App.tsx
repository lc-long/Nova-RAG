import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import './App.css'

function App() {
  const [currentDoc, setCurrentDoc] = useState<string | null>(null)

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar currentDoc={currentDoc} onSelectDoc={setCurrentDoc} />
      <ChatArea currentDoc={currentDoc} />
    </div>
  )
}

export default App