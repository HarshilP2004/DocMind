import React, { useEffect, useState } from 'react';
import { documentService } from '../services/api';
import { Document, DocumentMetadata } from '../types';
import { X, FileText, Calendar, DollarSign, Users, Award, ShieldAlert, Loader2 } from 'lucide-react';

interface MetadataModalProps {
  document: Document;
  onClose: () => void;
}

export const MetadataModal: React.FC<MetadataModalProps> = ({ document, onClose }) => {
  const [metadata, setMetadata] = useState<DocumentMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const data = await documentService.getMetadata(document.id);
        setMetadata(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load metadata. Make sure document indexing completed.');
      } finally {
        setLoading(false);
      }
    };
    fetchMetadata();
  }, [document.id]);

  const renderMetadataFields = () => {
    if (!metadata) return null;
    const data = metadata.extracted_data;

    // Helper to render key-value grid
    const renderRow = (icon: React.ReactNode, label: string, value: any) => {
      const displayValue = Array.isArray(value) ? value.join(', ') : value;
      return (
        <div key={label} className="flex items-start gap-3 p-3.5 bg-slate-900/40 border border-slate-700/50 rounded-xl">
          <div className="text-slate-400 mt-0.5">{icon}</div>
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</div>
            <div className="text-sm font-medium text-white mt-1">
              {displayValue !== null && displayValue !== undefined ? String(displayValue) : 'Not specified'}
            </div>
          </div>
        </div>
      );
    };

    switch (metadata.doc_type) {
      case 'Invoice':
      case 'Receipt':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderRow(<Users className="w-4 h-4 text-emerald-400" />, 'Vendor / Merchant', data.vendor || data.merchant)}
            {renderRow(<FileText className="w-4 h-4 text-cyan-400" />, 'Invoice Number', data.invoice_number)}
            {renderRow(<Calendar className="w-4 h-4 text-purple-400" />, 'Invoice Date', data.date)}
            {renderRow(<Award className="w-4 h-4 text-pink-400" />, 'Tax / GST Number', data.gst)}
            {renderRow(<DollarSign className="w-4 h-4 text-yellow-400" />, 'Total Amount', data.amount !== undefined ? `${data.currency || 'INR'} ${data.amount.toLocaleString()}` : null)}
          </div>
        );
      case 'Contract':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderRow(<Users className="w-4 h-4 text-emerald-400" />, 'Contracting Parties', data.parties)}
            {renderRow(<Calendar className="w-4 h-4 text-cyan-400" />, 'Effective Date', data.effective_date)}
            {renderRow(<Calendar className="w-4 h-4 text-red-400" />, 'Expiry Date', data.expiry_date)}
            {renderRow(<Award className="w-4 h-4 text-purple-400" />, 'Governing Law', data.governing_law)}
          </div>
        );
      case 'Medical Report':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderRow(<Users className="w-4 h-4 text-blue-400" />, 'Patient Name', data.patient_name)}
            {renderRow(<Calendar className="w-4 h-4 text-cyan-400" />, 'Report Date', data.report_date)}
            {renderRow(<Award className="w-4 h-4 text-indigo-400" />, 'Physician / Tester', data.doctor_name)}
            {renderRow(<FileText className="w-4 h-4 text-emerald-400" />, 'Primary Diagnosis', data.diagnosis)}
          </div>
        );
      case 'ID':
      case 'Passport':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderRow(<Users className="w-4 h-4 text-blue-400" />, 'Holder Full Name', data.full_name)}
            {renderRow(<FileText className="w-4 h-4 text-cyan-400" />, 'Document Number', data.id_number)}
            {renderRow(<Calendar className="w-4 h-4 text-emerald-400" />, 'Issue Date', data.issue_date)}
            {renderRow(<Calendar className="w-4 h-4 text-red-400" />, 'Expiry Date', data.expiry_date)}
            {renderRow(<Award className="w-4 h-4 text-purple-400" />, 'Nationality', data.nationality)}
          </div>
        );
      default:
        // Render dynamic attributes for general categories
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(data).map(([key, val]) => {
              const formattedKey = key.replace(/_/g, ' ');
              return renderRow(<FileText className="w-4 h-4 text-cyan-400" />, formattedKey, val);
            })}
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-700">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-500" />
              Document Intelligence Metadata
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">{document.filename}</p>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-700 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 bg-slate-800/40">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
              <span className="text-sm">Querying metadata models...</span>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center p-6 bg-red-950/20 border border-red-900/30 rounded-xl text-center">
              <ShieldAlert className="w-8 h-8 text-red-500 mb-2" />
              <p className="text-sm font-semibold text-red-200">Metadata Extraction Unavailable</p>
              <p className="text-xs text-slate-400 mt-1 max-w-md">{error}</p>
            </div>
          )}

          {metadata && (
            <div className="space-y-6">
              {/* Classification Tag */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Classification:</span>
                <span className="px-3 py-1 bg-brand-500/10 border border-brand-500/30 text-brand-400 rounded-full text-xs font-bold uppercase tracking-wider">
                  {metadata.doc_type}
                </span>
              </div>

              {/* Data Grid */}
              {renderMetadataFields()}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-5 border-t border-slate-700 bg-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
