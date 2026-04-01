import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User, AlertCircle } from 'lucide-react'
import { askQuestion } from '../api/client'
import SourceViewer from './SourceViewer'

export default function ChatBox({ hasDocuments }) {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, loading])

    const sendMessage = async () => {
        const question = input.trim()
        if (!question || loading) return

        setMessages((prev) => [...prev, { role: 'user', text: question }])
        setInput('')
        setLoading(true)

        try {
            const res = await askQuestion(question)
            const { answer, retrieved_chunks, model_used } = res.data
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', text: answer, chunks: retrieved_chunks, model: model_used },
            ])
        } catch (err) {
            const msg = err.response?.data?.detail || 'Something went wrong. Please try again.'
            setMessages((prev) => [...prev, { role: 'error', text: msg }])
        } finally {
            setLoading(false)
        }
    }

    const onKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    return (
        <div className="flex flex-col h-full">
            {/* Message list */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center py-12">
                        <Bot className="w-10 h-10 text-gray-700 mb-3" />
                        <p className="text-gray-500 text-sm">
                            {hasDocuments
                                ? 'Ask anything about your indexed documents.'
                                : 'Upload a document to get started.'}
                        </p>
                    </div>
                )}

                {messages.map((msg, i) => {
                    if (msg.role === 'user') {
                        return (
                            <div key={i} className="flex items-start gap-3 justify-end">
                                <div className="max-w-[80%] bg-indigo-600/30 border border-indigo-700/50 text-gray-200 text-sm rounded-2xl rounded-tr-sm px-4 py-3">
                                    {msg.text}
                                </div>
                                <div className="shrink-0 w-7 h-7 rounded-full bg-indigo-700/50 flex items-center justify-center">
                                    <User className="w-4 h-4 text-indigo-300" />
                                </div>
                            </div>
                        )
                    }

                    if (msg.role === 'error') {
                        return (
                            <div key={i} className="flex items-start gap-3">
                                <div className="shrink-0 w-7 h-7 rounded-full bg-red-900/50 flex items-center justify-center">
                                    <AlertCircle className="w-4 h-4 text-red-400" />
                                </div>
                                <div className="max-w-[80%] bg-red-950/50 border border-red-800 text-red-300 text-sm rounded-2xl rounded-tl-sm px-4 py-3">
                                    {msg.text}
                                </div>
                            </div>
                        )
                    }

                    return (
                        <div key={i} className="flex items-start gap-3">
                            <div className="shrink-0 w-7 h-7 rounded-full bg-gray-800 flex items-center justify-center">
                                <Bot className="w-4 h-4 text-indigo-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="bg-gray-900 border border-gray-800 text-gray-200 text-sm rounded-2xl rounded-tl-sm px-4 py-3 whitespace-pre-wrap leading-relaxed">
                                    {msg.text}
                                </div>
                                <SourceViewer chunks={msg.chunks} />
                                {msg.model && (
                                    <p className="text-xs text-gray-600 mt-1.5 pl-1">
                                        via {msg.model}
                                    </p>
                                )}
                            </div>
                        </div>
                    )
                })}

                {loading && (
                    <div className="flex items-start gap-3">
                        <div className="shrink-0 w-7 h-7 rounded-full bg-gray-800 flex items-center justify-center">
                            <Bot className="w-4 h-4 text-indigo-400" />
                        </div>
                        <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
                            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input row */}
            <div className="pt-4 border-t border-gray-800 mt-4">
                <div className="flex gap-2 items-end">
                    <textarea
                        rows={1}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder={hasDocuments ? 'Ask a question…' : 'Upload a document first'}
                        disabled={!hasDocuments || loading}
                        className="flex-1 resize-none bg-gray-900 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!input.trim() || !hasDocuments || loading}
                        className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
                    >
                        <Send className="w-4 h-4 text-white" />
                    </button>
                </div>
                <p className="text-xs text-gray-700 mt-1.5 pl-1">Enter to send · Shift+Enter for newline</p>
            </div>
        </div>
    )
}
