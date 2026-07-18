import axios from 'axios';
import { Document, DocumentMetadata, ChatSession, ChatMessage } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

// Generate or retrieve persistent visitor ID
let visitorId = localStorage.getItem('docmind_visitor_id');
if (!visitorId) {
  visitorId = crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).substring(2) + Date.now().toString(36);
  localStorage.setItem('docmind_visitor_id', visitorId);
}

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to inject X-Visitor-ID header for stateless visitor routing
apiClient.interceptors.request.use((config) => {
  if (visitorId) {
    config.headers['X-Visitor-ID'] = visitorId;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const documentService = {
  async upload(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<Document>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  async list() {
    const res = await apiClient.get<Document[]>('/documents');
    return res.data;
  },

  async getMetadata(docId: number) {
    const res = await apiClient.get<DocumentMetadata>(`/documents/${docId}/metadata`);
    return res.data;
  },

  async delete(docId: number) {
    const res = await apiClient.delete(`/documents/${docId}`);
    return res.data;
  },
};

export const chatService = {
  async createSession(title: string = 'New Chat') {
    const res = await apiClient.post<ChatSession>('/chat/sessions', { title });
    return res.data;
  },

  async listSessions() {
    const res = await apiClient.get<ChatSession[]>('/chat/sessions');
    return res.data;
  },

  async getMessages(sessionId: number) {
    const res = await apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
    return res.data;
  },

  async deleteSession(sessionId: number) {
    const res = await apiClient.delete(`/chat/sessions/${sessionId}`);
    return res.data;
  },

  async getLimitStatus() {
    const res = await apiClient.get<{ limit: number, used: number, remaining: number }>('/chat/limit-status');
    return res.data;
  },

  // Custom SSE Stream Reader for Chat Queries
  async streamQuery(
    query: string,
    sessionId: number | null,
    documentIds: number[] | null,
    onCitations: (citations: any[]) => void,
    onToken: (token: string) => void,
    onError: (err: string) => void,
    onDone: () => void
  ) {
    try {
      const response = await fetch(`${API_BASE}/chat/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Visitor-ID': visitorId || '',
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
          document_ids: documentIds,
        }),
      });

      if (!response.ok) {
        // Retrieve error message if possible
        let errorMsg = `HTTP error! status: ${response.status}`;
        try {
          const errData = await response.json();
          if (errData?.detail) {
            errorMsg = errData.detail;
          }
        } catch (e) { }
        throw new Error(errorMsg);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) {
        throw new Error('ReadableStream not supported in this browser.');
      }

      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Save the last partial line back to the buffer
        buffer = lines.pop() || '';

        let currentEvent = '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.replace('event: ', '').trim();
          } else if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.replace('data: ', '').trim();

            if (currentEvent === 'citations') {
              try {
                const citations = JSON.parse(dataStr);
                onCitations(citations);
              } catch (e) {
                console.error('Error parsing citation json:', e);
              }
            } else if (currentEvent === 'token') {
              try {
                const tokenData = JSON.parse(dataStr);
                onToken(tokenData.token);
              } catch (e) {
                console.error('Error parsing token json:', e);
              }
            } else if (currentEvent === 'error') {
              try {
                const errorData = JSON.parse(dataStr);
                onError(errorData.error);
              } catch (e) {
                onError('Stream error.');
              }
            } else if (currentEvent === 'done') {
              onDone();
            }
          }
        }
      }

      onDone();
    } catch (error: any) {
      onError(error?.message || 'Network stream error.');
    }
  }
};
