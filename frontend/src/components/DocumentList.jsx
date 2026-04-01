import { useState } from 'react'
import { FileText, Trash2, Loader2, FileSpreadsheet, File } from 'lucide-react'
import { deleteDocument } from '../api/client'

const FILE_ICONS = {
    pdf: FileText,
    txt: File,
    docx: FileText,
    csv: FileSpreadsheet,
    xlsx: FileSpreadsheet,
}

const FILE_COLORS = {
    pdf: 'text-red-400',
    txt: 'text-blue-400',
    docx: 'text-blue-500',
    csv: 'text-emerald-400',
    xlsx: 'text-emerald-500',
}

export default function DocumentList({ documents, onDelete }) {
    const [deletingId, setDeletingId] = useState(null)

    const handleDelete = async (doc) => {
        if (!window.confirm(`Remove "${doc.filename}" from the index?`)) return
        setDeletingId(doc.id)
        try {
            await deleteDocument(doc.id)
            onDelete(doc.id)
        } catch (err) {
            alert('Failed to delete document.')
        } finally {
            setDeletingId(null)
        }
    }

    if (documents.length === 0) {
        return (
            <p className="text-sm text-gray-500 text-center py-6">
                No documents indexed yet.
            </p>
        )
    }

    return (
        <ul className="space-y-2">
            {documents.map((doc) => {
                const Icon = FILE_ICONS[doc.file_type] || File
                const colorClass = FILE_COLORS[doc.file_type] || 'text-gray-400'
                const isDeleting = deletingId === doc.id

                return (
                    <li
                        key={doc.id}
                        className="flex items-center gap-3 bg-gray-900 rounded-lg px-3 py-2.5 group"
                    >
                        <Icon className={`w-5 h-5 shrink-0 ${colorClass}`} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-200 truncate">{doc.filename}</p>
                            <p className="text-xs text-gray-500">
                                {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} · {doc.chunk_count} chunks
                            </p>
                        </div>
                        <button
                            onClick={() => handleDelete(doc)}
                            disabled={isDeleting}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-600 hover:text-red-400 disabled:opacity-50"
                            title="Remove from index"
                        >
                            {isDeleting
                                ? <Loader2 className="w-4 h-4 animate-spin" />
                                : <Trash2 className="w-4 h-4" />}
                        </button>
                    </li>
                )
            })}
        </ul>
    )
}