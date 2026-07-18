import React, { useState, useEffect, useRef } from 'react';
import { chatService } from '../services/api';
import { ChatSession, ChatMessage, Document, Citation } from '../types';
import { 
  Send, Sparkles, MessageSquare, Plus, Trash2, 
  BookOpen, CornerDownRight, Loader2, Info
} from 'lucide-react';

interface ChatConsoleProps {
  selectedDocs: number[];
  documents: Document[];
}

export const ChatConsole: React.FC<ChatConsoleProps> = ({ selectedDocs, documents }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  
  // Streaming State
  const [streamingText, setStreamingText] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');
  const [limitStatus, setLimitStatus] = useState<{ limit: number, used: number, remaining: number } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat sessions on mount
  useEffect(() => {
    fetchSessions();
    fetchLimitStatus();
  }, []);

  const fetchLimitStatus = async () => {
    try {
      const status = await chatService.getLimitStatus();
      setLimitStatus(status);
    } catch (err) {
      console.error('Failed to load limit status:', err);
    }
  };

  // Fetch messages when active session changes
  useEffect(() => {
    if (activeSession) {
      fetchMessages(activeSession.id);
    } else {
      setMessages([]);
    }
  }, [activeSession]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const fetchSessions = async () => {
    try {
      const data = await chatService.listSessions();
      setSessions(data);
      if (data.length > 0 && !activeSession) {
        setActiveSession(data[0]);
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  };

  const fetchMessages = async (sessionId: number) => {
    try {
      const data = await chatService.getMessages(sessionId);
      setMessages(data);
    } catch (err) {
      console.error('Failed to load chat messages:', err);
    }
  };

  const handleCreateSession = async () => {
    try {
      const sess = await chatService.createSession('New Chat');
      setSessions([sess, ...sessions]);
      setActiveSession(sess);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleDeleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chatService.deleteSession(sessionId);
      const updated = sessions.filter(s => s.id !== sessionId);
      setSessions(updated);
      if (activeSession?.id === sessionId) {
        setActiveSession(updated.length > 0 ? updated[0] : null);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    setError('');
    const queryText = inputValue;
    setInputValue('');
    
    // Append the user's message locally instantly for UX
    const userMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: queryText,
      citations: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    
    // Setup streaming placeholders
    setIsStreaming(true);
    setStreamingText('');
    setStreamingCitations([]);

    let currentSessionId = activeSession?.id || null;

    try {
      await chatService.streamQuery(
        queryText,
        currentSessionId,
        selectedDocs.length > 0 ? selectedDocs : null,
        // On Citations Event
        (citations) => {
          setStreamingCitations(citations);
        },
        // On Token Event
        (token) => {
          setStreamingText(prev => prev + token);
        },
        // On Error Event
        (err) => {
          setError(err);
          setIsStreaming(false);
          fetchLimitStatus();
        },
        // On Done Event
        async () => {
          setIsStreaming(false);
          setStreamingText('');
          setStreamingCitations([]);
          await fetchLimitStatus();
          // Reload sessions if a new session was auto-created
          if (!currentSessionId) {
            const data = await chatService.listSessions();
            setSessions(data);
            if (data.length > 0) {
              const matching = data.find(s => s.title.startsWith(queryText.substring(0, 15)));
              const targetSess = matching || data[0];
              setActiveSession(targetSess);
              await fetchMessages(targetSess.id);
            }
          } else {
            await fetchMessages(currentSessionId);
          }
        }
      );
    } catch (err: any) {
      setError(err.message || 'Stream processing failed');
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-80px)] bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl">
      {/* Sidebar - Sessions Panel */}
      <div className="w-64 bg-slate-950/40 border-r border-slate-800 p-4 flex flex-col justify-between">
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* New Chat Button */}
          <button
            onClick={handleCreateSession}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-brand-600/10 hover:bg-brand-600/20 border border-brand-500/20 text-brand-400 font-semibold rounded-xl text-sm transition cursor-pointer mb-4"
          >
            <Plus className="w-4 h-4" />
            New Thread
          </button>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {sessions.map((sess) => (
              <div
                key={sess.id}
                onClick={() => setActiveSession(sess)}
                className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition text-left group ${
                  activeSession?.id === sess.id
                    ? 'bg-slate-800 text-white font-medium border border-slate-700/50'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <MessageSquare className="w-4 h-4 flex-shrink-0 text-slate-500" />
                  <span className="text-sm truncate pr-2">{sess.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(sess.id, e)}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-slate-700 hover:text-red-400 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col bg-slate-900/40 justify-between">
        {/* Active Scope / Banner */}
        <div className="px-6 py-3 border-b border-slate-800 bg-slate-950/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4.5 h-4.5 text-brand-400 animate-pulse" />
            <span className="text-xs font-semibold text-slate-300">Grounded Document Query Engine</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="px-2 py-0.5 bg-slate-800 rounded font-semibold text-slate-300">
              {selectedDocs.length > 0 
                ? `${selectedDocs.length} files selected` 
                : 'All Documents'
              }
            </span>
          </div>
        </div>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 text-slate-500 max-w-lg mx-auto">
              <BookOpen className="w-12 h-12 text-slate-700 mb-3" />
              <h4 className="text-sm font-semibold text-slate-300">Ask your documents anything</h4>
              <p className="text-xs text-slate-500 mt-1">
                Enter your question below. The intelligence platform will fetch semantic chunks, check cross-references, and synthesize an answer citing exact pages.
              </p>
              
              <div className="mt-4 p-3 bg-slate-950/20 border border-slate-800 rounded-xl text-left text-xs w-full">
                <div className="font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-cyan-500" />
                  Try asking things like:
                </div>
                <ul className="list-disc pl-4 space-y-1 mt-1 text-slate-500">
                  <li>"Find all invoices above ₹50,000."</li>
                  <li>"Which contracts expire next month?"</li>
                  <li>"Compare our cancellation policies."</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* Message Bubble */}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-md border ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white border-brand-500 rounded-tr-none'
                    : 'bg-slate-800 text-slate-100 border-slate-700/80 rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>

              {/* Citations block for Assistant message */}
              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <div className="mt-2.5 ml-2 space-y-1.5 max-w-[80%]">
                  <div className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                    <CornerDownRight className="w-3 h-3" /> Sources Referenced:
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                    {msg.citations.map((cite, index) => (
                      <div key={index} className="p-2.5 bg-slate-950/20 border border-slate-800 rounded-xl text-xs group relative">
                        <div className="font-semibold text-slate-300 flex items-center gap-1 truncate">
                          <BookOpen className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />
                          {cite.document_name}
                          {cite.page_number && <span className="text-[10px] bg-slate-800 px-1 py-0.5 rounded text-slate-400 ml-1">Page {cite.page_number}</span>}
                        </div>
                        <p className="text-slate-400 mt-1 line-clamp-2 italic text-[11px]">
                          "{cite.content}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Streaming Assistant bubble */}
          {isStreaming && (streamingText || streamingCitations.length > 0) && (
            <div className="flex flex-col items-start">
              <div className="max-w-[80%] rounded-2xl px-4 py-3 text-sm bg-slate-800 text-slate-100 border border-slate-700/80 rounded-tl-none shadow-md">
                {streamingText || (
                  <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-400" />
                    Synthesizing response...
                  </span>
                )}
              </div>
              
              {streamingCitations.length > 0 && (
                <div className="mt-2.5 ml-2 space-y-1.5 max-w-[80%]">
                  <div className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                    <CornerDownRight className="w-3 h-3" /> Sources Referenced:
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                    {streamingCitations.map((cite, index) => (
                      <div key={index} className="p-2.5 bg-slate-950/20 border border-slate-800 rounded-xl text-xs">
                        <div className="font-semibold text-slate-300 flex items-center gap-1 truncate">
                          <BookOpen className="w-3.5 h-3.5 text-brand-400 flex-shrink-0" />
                          {cite.document_name}
                          {cite.page_number && <span className="text-[10px] bg-slate-800 px-1 py-0.5 rounded text-slate-400 ml-1">Page {cite.page_number}</span>}
                        </div>
                        <p className="text-slate-400 mt-1 line-clamp-2 italic text-[11px]">
                          "{cite.content}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-xl text-xs text-red-200 w-fit">
              Error streaming query: {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/15 flex flex-col gap-2">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask a question or enter a search query..."
              disabled={isStreaming}
              className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-xl text-sm text-white placeholder-slate-500 transition outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isStreaming}
              className="px-4 bg-brand-600 hover:bg-brand-500 text-white rounded-xl flex items-center justify-center transition shadow-lg shadow-brand-500/10 cursor-pointer disabled:opacity-40"
            >
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </form>
          {limitStatus && (
            <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
              <span className="flex items-center gap-1 select-none">
                <Info className="w-3.5 h-3.5 text-slate-500" />
                Remaining queries: <strong className="text-slate-300">{limitStatus.remaining}</strong> / {limitStatus.limit} today
              </span>
              <span className="select-none">Resets daily at 00:00 UTC</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
