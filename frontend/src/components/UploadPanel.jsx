import { useState, useRef } from 'react'
import { Upload, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { uploadDocument } from '../api/client'

const ACCEPTED = '.pdf,.txt,.docx,.csv,.xlsx'

export default function UploadPanel({ onUploadSuccess }) {
    const [dragging, setDragging] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [status, setStatus] = useState(null) // { type: 'success'|'error', message }
    const inputRef = useRef(null)

    const handleFile = async (file) => {
        if (!file) return
        setUploading(true)
        setProgress(0)
        setStatus(null)

        try {
            const res = await uploadDocument(file, setProgress)
            setStatus({ type: 'success', message: res.data.message })
            onUploadSuccess(res.data.document)
        } catch (err) {
            const msg = err.response?.data?.detail || 'Upload failed. Please try again.'
            setStatus({ type: 'error', message: msg })
        } finally {
            setUploading(false)
            setProgress(0)
        }
    }

    const onDrop = (e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) handleFile(file)
    }

    return (
        <div className="space-y-3">
            {/* Drop zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => !uploading && inputRef.current?.click()}
                className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
          ${dragging ? 'border-indigo-400 bg-indigo-950/30' : 'border-gray-700 hover:border-gray-500 bg-gray-900/50'}
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept={ACCEPTED}
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files[0])}
                />

                {uploading ? (
                    <div className="space-y-3">
                        <Loader2 className="w-8 h-8 mx-auto text-indigo-400 animate-spin" />
                        <p className="text-sm text-gray-400">Indexing document…</p>
                        <div className="w-full bg-gray-800 rounded-full h-1.5">
                            <div
                                className="bg-indigo-500 h-1.5 rounded-full transition-all"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                ) : (
                    <>
                        <Upload className="w-8 h-8 mx-auto text-gray-500 mb-3" />
                        <p className="text-sm text-gray-300 font-medium">Drop a file or click to upload</p>
                        <p className="text-xs text-gray-500 mt-1">PDF, TXT, DOCX, CSV, XLSX · max 20 MB</p>
                    </>
                )}
            </div>

            {/* Status message */}
            {status && (
                <div className={`flex items-start gap-2 rounded-lg p-3 text-sm ${status.type === 'success'
                        ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-800'
                        : 'bg-red-950/50 text-red-300 border border-red-800'
                    }`}>
                    {status.type === 'success'
                        ? <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                    <span>{status.message}</span>
                </div>
            )}
        </div>
    )
}