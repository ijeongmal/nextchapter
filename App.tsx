import React, { useState } from 'react';
import { analyzeBooks } from './services/geminiService';
import BookInput from './components/BookInput';
import NetworkGraph from './components/NetworkGraph';
import BookDetail from './components/BookDetail';
import { GraphData, BookNode } from './types';
import { Network } from 'lucide-react';

const App: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<BookNode | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (b1: string, b2: string, b3: string) => {
    setLoading(true);
    setError(null);
    setGraphData(null);
    setSelectedNode(null);

    // Check for API Key
    const apiKey = process.env.API_KEY;
    if (!apiKey) {
      setLoading(false);
      // Wait a moment to ensure window.aistudio is ready if we were to use it,
      // but per prompt instructions, we assume pre-configured env or handle it here.
      // Since we need to prompt the user if missing:
      if (window.aistudio && window.aistudio.openSelectKey) {
        try {
            const hasKey = await window.aistudio.hasSelectedApiKey();
            if(!hasKey) {
                await window.aistudio.openSelectKey();
            }
            // Retry logic would ideally go here, but for now we just stop loading and ask them to click again
             setError("API Key selected. Please try again.");
             setLoading(false);
             return;
        } catch (e) {
            setError("Failed to select API key.");
            setLoading(false);
            return;
        }
      } else {
        setError("API Key not found in environment.");
        setLoading(false);
        return;
      }
    }

    try {
      const data = await analyzeBooks(b1, b2, b3);
      setGraphData(data);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during analysis.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-screen bg-slate-900 text-slate-200 flex flex-col overflow-hidden relative">
      {/* Header */}
      <header className="h-16 border-b border-slate-800 flex items-center px-6 bg-slate-900/90 z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg">
             <Network className="text-emerald-400 w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">Literary Nexus</h1>
            <p className="text-xs text-slate-500">AI-Powered Book Recommendation Network</p>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 relative">
        
        {/* If no data, show input form centered */}
        {!graphData && !loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 z-10">
            <div className="mb-8 text-center max-w-lg">
              <h2 className="text-3xl font-bold text-white mb-4">Discover Your Literary Constellation</h2>
              <p className="text-slate-400">
                Enter 3 books you love. We'll analyze their writing style, difficulty, and philosophy to build a personalized reading map.
              </p>
            </div>
            <BookInput onAnalyze={handleAnalyze} isLoading={loading} />
            {error && (
              <div className="mt-4 bg-red-500/10 border border-red-500/50 text-red-200 px-4 py-2 rounded-lg text-sm">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Loading State */}
        {loading && (
           <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900 z-50">
             <div className="relative">
               <div className="w-16 h-16 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
               <div className="absolute inset-0 flex items-center justify-center">
                 <Network className="w-6 h-6 text-emerald-500 animate-pulse" />
               </div>
             </div>
             <p className="mt-6 text-emerald-400 font-medium animate-pulse">Analyzing literary patterns...</p>
             <p className="text-slate-500 text-sm mt-2">Creating neural connections between books</p>
           </div>
        )}

        {/* Visualization Area */}
        {graphData && (
          <div className="w-full h-full relative">
            <NetworkGraph 
              data={graphData} 
              onNodeClick={(node) => setSelectedNode(node)} 
            />
            
            {/* Overlay Controls */}
            <div className="absolute top-4 right-4 flex gap-2">
                 <button 
                  onClick={() => {
                    setGraphData(null);
                    setSelectedNode(null);
                  }}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg text-sm font-medium border border-slate-600 transition-colors shadow-lg"
                 >
                   New Analysis
                 </button>
            </div>
            
            {/* Details Panel */}
            <BookDetail 
              node={selectedNode} 
              onClose={() => setSelectedNode(null)} 
            />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
