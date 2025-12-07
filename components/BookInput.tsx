import React, { useState } from 'react';
import { BookOpen, Search } from 'lucide-react';

interface BookInputProps {
  onAnalyze: (b1: string, b2: string, b3: string) => void;
  isLoading: boolean;
}

const BookInput: React.FC<BookInputProps> = ({ onAnalyze, isLoading }) => {
  const [b1, setB1] = useState('');
  const [b2, setB2] = useState('');
  const [b3, setB3] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (b1 && b2 && b3) {
      onAnalyze(b1, b2, b3);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-slate-800/50 backdrop-blur-md p-6 rounded-xl border border-slate-700 shadow-2xl z-10">
      <div className="flex items-center gap-2 mb-6">
        <BookOpen className="text-emerald-400 w-6 h-6" />
        <h2 className="text-xl font-bold text-slate-100">취향 분석 시작하기</h2>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">Book 1</label>
          <input
            type="text"
            value={b1}
            onChange={(e) => setB1(e.target.value)}
            placeholder="예: 데미안"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">Book 2</label>
          <input
            type="text"
            value={b2}
            onChange={(e) => setB2(e.target.value)}
            placeholder="예: 총, 균, 쇠"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">Book 3</label>
          <input
            type="text"
            value={b3}
            onChange={(e) => setB3(e.target.value)}
            placeholder="예: 1984"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !b1 || !b2 || !b3}
          className={`w-full flex items-center justify-center gap-2 mt-6 py-3 rounded-lg font-semibold text-white transition-all transform active:scale-95 ${
            isLoading 
              ? 'bg-slate-600 cursor-not-allowed opacity-70' 
              : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-900/20'
          }`}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>분석 및 네트워크 생성 중...</span>
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              <span>네트워크 생성</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default BookInput;
