export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Document {
  id: number;
  filename: string;
  file_type: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  ocr_used: boolean;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentMetadata {
  document_id: number;
  doc_type: string;
  extracted_data: Record<string, any>;
  created_at: string;
}

export interface Citation {
  document_name: string;
  page_number: number | null;
  content: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}
