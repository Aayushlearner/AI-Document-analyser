import { useState, useEffect } from 'react'
import { Brain, FileStack } from 'lucide-react'
import UploadPanel from './components/UploadPanel'
import DocumentList from './components/DocumentList'
import ChatBox from './components/ChatBox'
import { listDocuments } from './api/client'

export default function App() {
    const [documents, setDocuments] = useState([])
    const [loadingDocs, setLoadingDocs] = useState(true)

    useEffect(() => {
        listDocuments()
            .then((res) => setDocuments(res.data.documents))
            .catch(() => {})
            .finally(() => setLoadingDocs(false))
    }, [])

    const handleUploadSuccess = (doc) => {
        setDocuments((prev) => [doc, ...prev])
    }

    const handleDelete = (id) => {
        setDocuments((prev) => prev.filter((d) => d.id !== id))
    }

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
            {/* Header */}
            <header className="border-b border-gray-800 px-6 py-4 flex items-center gap-3">
                <Brain className="w-6 h-6 text-indigo-400" />
                <h1 className="text-lg font-semibold tracking-tight">AI Document Analyser</h1>
            </header>

            {/* Main layout */}
            <main className="flex-1 flex overflow-hidden">
                {/* Left sidebar — upload + document list */}
                <aside className="w-80 shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
                    <div className="p-4 border-b border-gray-800">
                        <UploadPanel onUploadSuccess={handleUploadSuccess} />
                    </div>

                    <div className="flex-1 overflow-y-auto p-4">
                        <div className="flex items-center gap-2 mb-3">
                            <FileStack className="w-4 h-4 text-gray-500" />
                            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                                Indexed Documents
                            </h2>
                            {!loadingDocs && (
                                <span className="ml-auto text-xs bg-gray-800 text-gray-400 rounded-full px-2 py-0.5">
                                    {documents.length}
                                </span>
                            )}
                        </div>

                        {loadingDocs ? (
                            <p className="text-xs text-gray-600 text-center py-6">Loading…</p>
                        ) : (
                            <DocumentList documents={documents} onDelete={handleDelete} />
                        )}
                    </div>
                </aside>

                {/* Right panel — chat */}
                <section className="flex-1 flex flex-col overflow-hidden p-6">
                    <ChatBox hasDocuments={documents.length > 0} />
                </section>
            </main>
        </div>
    )
}
