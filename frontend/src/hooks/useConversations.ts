import { useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'

export function useConversations() {
  const {
    conversations, conversationId,
    setConversationId, setMessages,
    loadConversations, loadConversationMessages, removeConversation,
  } = useAppStore()

  useEffect(() => { loadConversations() }, [loadConversations])

  const handleSelectConversation = (id: string | null) => {
    setConversationId(id)
  }

  const handleNewChat = () => {
    setConversationId(null)
    setMessages([])
  }

  const handleDeleteConversation = async (id: string) => {
    await removeConversation(id)
  }

  return {
    conversations,
    conversationId,
    handleSelectConversation,
    handleNewChat,
    handleDeleteConversation,
    loadConversationMessages,
    loadConversations,
  }
}
