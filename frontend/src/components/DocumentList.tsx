import React, { useState, useEffect, useRef } from 'react';
import { documentService } from '../services/api';
import { Document } from '../types';
import { 
  UploadCloud, FileText, CheckCircle2, AlertTriangle, 
  Trash2, Search, Loader2, Eye, ShieldCheck
} from 'lucide-react';

interface DocumentListProps {
  onSelectedDocsChange: (docIds: number[]) => void;
  selectedDocs: number[];
  onViewMetadata: (doc: Document) => void;
  documents: Document[];
  onRefreshDocs: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  onSelectedDocsChange,
  selectedDocs,
  onViewMetadata,
  documents,
  onRefreshDocs
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [importingSample, setImportingSample] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportSample = async (filename: string, displayName: string) => {
    setUploadError('');
    setImportingSample(displayName);
    try {
      const response = await fetch(`/samples/${filename}`);
      if (!response.ok) {
        throw new Error(`Failed to retrieve sample file: ${response.statusText}`);
      }
      const blob = await response.blob();
      const file = new File([blob], filename, { type: 'application/pdf' });
      await documentService.upload(file);
      onRefreshDocs();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to import sample PDF.');
    } finally {
      setImportingSample(null);
    }
  };

  // Poll for document status updates if any document is currently indexing
  useEffect(() => {
    const hasUnfinishedDocs = documents.some(
      d => d.status === 'uploaded' || d.status === 'processing'
    );

    if (hasUnfinishedDocs) {
      const interval = setInterval(() => {
        onRefreshDocs();
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [documents, onRefreshDocs]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    
    setUploadError('');
    setUploading(true);
    
    try {
      // Process one by one for background tasks
      for (let i = 0; i < files.length; i++) {
        await documentService.upload(files[i]);
      }
      onRefreshDocs();
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Failed to upload document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handleFileUpload(e.dataTransfer.files);
  };

  const handleDelete = async (docId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this document? All chunks and extracted metadata will be permanently deleted.')) return;
    
    try {
      await documentService.delete(docId);
      onRefreshDocs();
      // Remove from selection if deleted
      if (selectedDocs.includes(docId)) {
        onSelectedDocsChange(selectedDocs.filter(id => id !== docId));
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const toggleSelectDoc = (docId: number) => {
    if (selectedDocs.includes(docId)) {
      onSelectedDocsChange(selectedDocs.filter(id => id !== docId));
    } else {
      onSelectedDocsChange([...selectedDocs, docId]);
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/40 border border-emerald-800/60 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/40 border border-cyan-800/60 text-cyan-400 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing
          </span>
        );
      case 'uploaded':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Queued
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/40 border border-red-800/60 text-red-400">
            <AlertTriangle className="w-3.5 h-3.5" /> Failed
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Upload Zone Panel */}
      <div className="lg:col-span-1 flex flex-col gap-4">
        <div
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="border-2 border-dashed border-slate-700 hover:border-brand-500 rounded-2xl p-6 flex flex-col items-center justify-center bg-slate-800/20 backdrop-blur-sm cursor-pointer transition min-h-[220px]"
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            multiple
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          
          <UploadCloud className="w-10 h-10 text-slate-500 mb-2 group-hover:text-brand-400" />
          <h4 className="text-sm font-semibold text-slate-300">Upload documents</h4>
          <p className="text-xs text-slate-500 mt-1 text-center">
            Drag and drop files here, or click to browse. Supports PDF, PNG, JPG, or JPEG.
          </p>
          
          {uploading && (
            <div className="mt-4 flex items-center gap-2 text-xs text-brand-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Uploading to secure pipeline...</span>
            </div>
          )}
        </div>

        {uploadError && (
          <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-xl text-xs text-red-300">
            {uploadError}
          </div>
        )}

        {/* Quick Import Samples Panel */}
        <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-2xl flex flex-col gap-2.5 shadow-sm">
          <h5 className="font-semibold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 select-none">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
            Quick-Import Recruiter Samples
          </h5>
          <p className="text-[11px] text-slate-500 -mt-1 leading-normal select-none">
            No files handy? Import these pre-set documents to test out document intelligence and RAG queries instantly.
          </p>
          <div className="grid grid-cols-1 gap-2 mt-1">
            {[
              { file: 'Gemini_Generated_Image_4ypj9l4ypj9l4ypj.pdf', label: 'Medical Report', desc: 'Patient Info (OCR + Classification)' },
              { file: 'Gemini_Generated_Image_i95fkki95fkki95f.pdf', label: 'Employment Contract', desc: 'Signing Parties & Governing Law' },
              { file: 'Gemini_Generated_Image_bj3exybj3exybj3e.pdf', label: 'Store Receipt', desc: 'Merchant, Items list & Total Value' },
              { file: 'pdfpage.pdf', label: 'Platform Manual', desc: 'Technical documentation & metadata' }
            ].map((sample) => (
              <button
                key={sample.file}
                type="button"
                disabled={uploading || importingSample !== null}
                onClick={() => handleImportSample(sample.file, sample.label)}
                className="flex flex-col items-start p-2.5 bg-slate-800/40 hover:bg-slate-800 border border-slate-700/50 hover:border-slate-600 rounded-xl text-left transition select-none disabled:opacity-40 cursor-pointer"
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-xs font-semibold text-slate-300">{sample.label}</span>
                  {importingSample === sample.label ? (
                    <span className="text-[10px] text-brand-400 flex items-center gap-1 animate-pulse">
                      <Loader2 className="w-3 h-3 animate-spin" /> Importing
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Import</span>
                  )}
                </div>
                <span className="text-[10px] text-slate-500 mt-0.5">{sample.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 bg-slate-800/30 border border-slate-800 rounded-2xl text-xs text-slate-400">
          <h5 className="font-semibold text-slate-300 mb-1 flex items-center gap-1">
            <ShieldCheck className="w-4 h-4 text-brand-400" /> Secure Processing Pipeline
          </h5>
          <p>
            Scanned documents are automatically deskewed and noise-filtered via OpenCV before running multi-model metadata models and local vector indexing.
          </p>
        </div>
      </div>

      {/* Documents Log Table Panel */}
      <div className="lg:col-span-2 bg-slate-800/20 backdrop-blur-sm border border-slate-800 rounded-2xl overflow-hidden shadow-lg flex flex-col justify-between">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/10 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="p-4 w-12 text-center">Scope</th>
                <th className="p-4">Document</th>
                <th className="p-4">OCR Status</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-center">Chunks</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-slate-500 text-sm">
                    No documents uploaded yet. Add some files to start querying.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr 
                    key={doc.id}
                    className={`hover:bg-slate-800/10 transition ${
                      selectedDocs.includes(doc.id) ? 'bg-brand-500/5' : ''
                    }`}
                  >
                    <td className="p-4 text-center">
                      <input
                        type="checkbox"
                        disabled={doc.status !== 'completed'}
                        checked={selectedDocs.includes(doc.id)}
                        onChange={() => toggleSelectDoc(doc.id)}
                        className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 h-4 w-4 cursor-pointer disabled:opacity-30"
                      />
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-brand-400 flex-shrink-0" />
                        <div>
                          <div className="text-sm font-semibold text-white max-w-[200px] truncate">{doc.filename}</div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">{doc.file_type} file</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                        doc.status !== 'completed'
                          ? 'text-slate-500 bg-slate-900/40 border border-slate-800'
                          : doc.ocr_used
                            ? 'text-yellow-400 bg-yellow-950/20 border border-yellow-900/30'
                            : 'text-indigo-400 bg-indigo-950/20 border border-indigo-900/30'
                      }`}>
                        {doc.status !== 'completed' ? 'Pending' : doc.ocr_used ? 'OCR Used' : 'Direct Text'}
                      </span>
                    </td>
                    <td className="p-4">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="p-4 text-center text-sm font-medium text-slate-300">
                      {doc.status === 'completed' ? doc.total_chunks : '—'}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          disabled={doc.status !== 'completed'}
                          onClick={() => onViewMetadata(doc)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-cyan-400 transition disabled:opacity-30 disabled:hover:text-slate-400 cursor-pointer"
                          title="Inspect extracted metadata"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(doc.id, e)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-red-400 transition cursor-pointer"
                          title="Delete document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
