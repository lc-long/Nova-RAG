import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { useAppStore } from '../store/useAppStore'

export function useDocuments() {
  const {
    docs, loadingDocs, currentDoc, previewDocId,
    setCurrentDoc, setPreviewDocId,
    loadDocs, uploadDocuments, removeDoc, removeDocs,
  } = useAppStore()

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleUpload = async (files: File[]) => {
    const { succeeded, failed } = await uploadDocuments(files)
    if (succeeded > 0) toast.success(`成功上传 ${succeeded} 个文档`)
    if (failed.length > 0) toast.error(`以下文件上传失败：${failed.join(', ')}`)
    loadDocs() // Refresh to get server-side status
  }

  const handleDelete = async (id: string) => {
    await removeDoc(id)
    toast.success('文档已删除')
  }

  const handleBatchDelete = async (ids: string[]) => {
    await removeDocs(ids)
    toast.success(`已删除 ${ids.length} 个文档`)
  }

  const handlePreview = (docId: string) => {
    setPreviewDocId(docId)
    setCurrentDoc(docId)
  }

  const handleClosePreview = () => setPreviewDocId(null)

  return {
    docs,
    loadingDocs,
    currentDoc,
    previewDocId,
    setCurrentDoc,
    handleUpload,
    handleDelete,
    handleBatchDelete,
    handlePreview,
    handleClosePreview,
  }
}
