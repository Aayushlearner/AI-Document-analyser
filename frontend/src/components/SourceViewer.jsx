import { useState } from 'react'
import { ChevronDown, ChevronRight, BookOpen } from 'lucide-react'

export default function SourceViewer({ chunks }) {
    const [open, setOpen] = useState(false)

    if (!chunks || chunks.length === 0) return null

    return (
        <div className="mt-3 border border-gray-800 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-900 hover:bg-gray-800 transition-colors text-sm text-gray-400"
            >
                {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <BookOpen className="w-4 h-4" />
                <span>
                    {chunks.length} source {chunks.length === 1 ? 'chunk' : 'chunks'} retrieved
                </span>
            </button>

            {open && (
                <div className="divide-y divide-gray-800/60">
                    {chunks.map((chunk, i) => (
                        <div key={chunk.chunk_id} className="px-4 py-3 bg-gray-950/50">
                            {/* Header */}
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                    <span className="bg-indigo-900/60 text-indigo-300 rounded px-1.5 py-0.5 font-mono">
                                        #{i + 1}
                                    </span>
                                    <span className="font-medium text-gray-400">{chunk.filename}</span>
                                    {chunk.page_number && (
                                        <span>· Page {chunk.page_number}</span>
                                    )}
                                </div>
                                <span
                                    className={`text-xs font-mono px-1.5 py-0.5 rounded ${chunk.similarity_score > 0.75
                                            ? 'bg-emerald-900/50 text-emerald-400'
                                            : chunk.similarity_score > 0.5
                                                ? 'bg-yellow-900/50 text-yellow-400'
                                                : 'bg-gray-800 text-gray-500'
                                        }`}
                                    title="Similarity score"
                                >
                                    {(chunk.similarity_score * 100).toFixed(1)}%
                                </span>
                            </div>

                            {/* Chunk content */}
                            <p className="text-xs text-gray-400 leading-relaxed line-clamp-4 font-mono whitespace-pre-wrap">
                                {chunk.content}
                            </p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}