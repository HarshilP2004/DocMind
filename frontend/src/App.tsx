import { useState, useEffect } from 'react';
import { DocumentList } from './components/DocumentList';
import { ChatConsole } from './components/ChatConsole';
import { MetadataModal } from './components/MetadataModal';
import { documentService } from './services/api';
import { Document } from './types';
import { 
  Sparkles, FileText, MessageSquare, 
  Layers, Cpu, Database, HelpCircle
} from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'documents' | 'chat'>('documents');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [activeMetaDoc, setActiveMetaDoc] = useState<Document | null>(null);

  // Fetch documents list on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const data = await documentService.list();
      setDocuments(data);
    } catch (err) {
      console.error('Failed to load documents list:', err);
    }
  };

  // Calculate Dashboard Metrics
  const totalChunks = documents.reduce((acc, doc) => acc + (doc.total_chunks || 0), 0);
  const ocrCount = documents.filter(d => d.status === 'completed' && d.ocr_used).length;
  const directTextCount = documents.filter(d => d.status === 'completed' && !d.ocr_used).length;
  const processingCount = documents.filter(d => d.status === 'uploaded' || d.status === 'processing').length;
  const failedCount = documents.filter(d => d.status === 'failed').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-slate-900/60 backdrop-blur-md border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 bg-gradient-to-tr from-brand-600 to-cyan-500 rounded-lg shadow-md shadow-brand-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-md font-bold tracking-tight text-white flex items-center gap-1.5">
              DocMind
              <span className="text-[10px] uppercase font-bold tracking-widest bg-brand-500/10 border border-brand-500/20 text-brand-400 px-1.5 py-0.5 rounded">
                PRO GRADE
              </span>
            </h1>
            <p className="text-[10px] text-slate-500">Document Intelligence & Reasoning Console</p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-slate-950/40 p-1 border border-slate-800 rounded-xl">
          <button
            onClick={() => setActiveTab('documents')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition cursor-pointer ${
              activeTab === 'documents'
                ? 'bg-slate-800 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            Documents
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition cursor-pointer ${
              activeTab === 'chat'
                ? 'bg-slate-800 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            AI Reasoning Panel
          </button>
        </div>

        {/* Decorative spot to balance header layout */}
        <div className="w-10 h-4" />
      </header>

      {/* Main Layout Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        
        {/* Metric Cards Banner (only visible in Documents tab) */}
        {activeTab === 'documents' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
              <div className="p-2.5 bg-brand-500/10 border border-brand-500/20 text-brand-400 rounded-xl">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Indexed Chunks</div>
                <div className="text-xl font-bold text-white mt-0.5">{totalChunks}</div>
              </div>
            </div>

            <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
              <div className="p-2.5 bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 rounded-xl">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">OCR Extraction</div>
                <div className="text-xl font-bold text-white mt-0.5">
                  {ocrCount} <span className="text-[10px] text-slate-400 font-medium font-mono">/ skipped {directTextCount}</span>
                </div>
              </div>
            </div>

            <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
              <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 rounded-xl">
                <Database className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Running Indexes</div>
                <div className="text-xl font-bold text-white mt-0.5">{processingCount}</div>
              </div>
            </div>

            <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-center gap-4">
              <div className="p-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl">
                <HelpCircle className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Failed Indexes</div>
                <div className="text-xl font-bold text-white mt-0.5">{failedCount}</div>
              </div>
            </div>
          </div>
        )}

        {/* View Routing */}
        <div className="relative">
          {activeTab === 'documents' ? (
            <DocumentList
              documents={documents}
              selectedDocs={selectedDocs}
              onSelectedDocsChange={(ids) => setSelectedDocs(ids)}
              onViewMetadata={(doc) => setActiveMetaDoc(doc)}
              onRefreshDocs={fetchDocuments}
            />
          ) : (
            <ChatConsole
              selectedDocs={selectedDocs}
              documents={documents}
            />
          )}
        </div>
      </main>

      {/* Floating Metadata Inspector Modal */}
      {activeMetaDoc && (
        <MetadataModal
          document={activeMetaDoc}
          onClose={() => setActiveMetaDoc(null)}
        />
      )}
    </div>
  );
}

export default App;
