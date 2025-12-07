import React from 'react';
import { BookNode, NodeType } from '../types';
import { X, User, Tag } from 'lucide-react';
import { COLORS } from '../constants';

interface BookDetailProps {
  node: BookNode | null;
  onClose: () => void;
}

const BookDetail: React.FC<BookDetailProps> = ({ node, onClose }) => {
  if (!node) return null;

  const color = COLORS[node.group % COLORS.length];

  return (
    <div className="absolute top-4 right-4 w-80 bg-slate-800/90 backdrop-blur-md rounded-xl border border-slate-600 shadow-2xl overflow-hidden z-20 flex flex-col max-h-[90vh]">
      {/* Header */}
      <div className="p-4 flex items-start justify-between border-b border-slate-700 bg-slate-800">
        <div>
          <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full text-slate-900 mb-2 inline-block`} style={{ backgroundColor: color }}>
            {node.type === NodeType.SEED ? 'Seed Book' : 'Recommendation'}
          </span>
          <h3 className="text-xl font-bold text-slate-100 leading-tight">{node.label}</h3>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4 overflow-y-auto custom-scrollbar">
        <div className="flex items-center gap-2 text-slate-300">
          <User size={16} className="text-slate-500" />
          <span className="text-sm font-medium">{node.author}</span>
        </div>

        <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Analysis</h4>
          <p className="text-sm text-slate-300 leading-relaxed">
            {node.description}
          </p>
        </div>
        
        {node.type === NodeType.RECOMMENDED && (
           <div className="flex items-start gap-2 text-xs text-slate-400 mt-2">
             <Tag size={14} className="mt-0.5" />
             <span>Connected due to style, difficulty, or shared philosophy.</span>
           </div>
        )}
      </div>
      
      {/* Footer Decoration */}
      <div className="h-1 w-full" style={{ backgroundColor: color }} />
    </div>
  );
};

export default BookDetail;
