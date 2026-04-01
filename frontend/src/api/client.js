import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 60000,
})

// Documents
export const uploadDocument = (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/api/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
            if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
        },
    })
}

export const listDocuments = () => api.get('/api/documents')

export const deleteDocument = (id) => api.delete(`/api/documents/${id}`)

// Query
export const askQuestion = (question, topK = 5) =>
    api.post('/api/query', { question, top_k: topK })