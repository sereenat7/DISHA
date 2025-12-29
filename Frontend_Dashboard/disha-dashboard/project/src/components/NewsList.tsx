import { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, Calendar, MapPin, FileText, ExternalLink } from 'lucide-react';
import { NewsItem } from '../types';
import { api } from '../services/api';

export default function NewsList() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.getDisasterNews();
      setNews(response.disasters || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch disaster news');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, []);

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl shadow-2xl border border-slate-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <FileText className="text-blue-400" size={24} />
          Latest Disaster News
        </h3>

        <button
          onClick={fetchNews}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700/50 text-white rounded-lg transition-all duration-200"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          <span className="text-sm font-medium">Refresh</span>
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="animate-spin text-blue-400" size={32} />
            <p className="text-slate-400">Loading disaster news...</p>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="text-red-200 font-medium">Error loading news</p>
            <p className="text-red-300 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && news.length === 0 && (
        <div className="text-center py-12">
          <AlertCircle className="mx-auto text-slate-500 mb-3" size={48} />
          <p className="text-slate-400">No disaster news available at the moment.</p>
        </div>
      )}

      {!loading && !error && news.length > 0 && (
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
          {news.map((item, index) => (
            <div
              key={index}
              className="bg-slate-700/30 hover:bg-slate-700/50 rounded-lg p-5 border border-slate-600/50 hover:border-slate-500 transition-all duration-200 group"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <h4 className="text-lg font-bold text-white group-hover:text-blue-300 transition-colors">
                  {item.headline}
                </h4>
                <span className="px-3 py-1 bg-red-500/20 text-red-300 text-xs font-semibold rounded-full whitespace-nowrap">
                  {item.type}
                </span>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-4">
                {item.summary}
              </p>

              <div className="space-y-2">
                {item.locations && item.locations.length > 0 && (
                  <div className="flex items-start gap-2 text-slate-400 text-sm">
                    <MapPin size={16} className="flex-shrink-0 mt-0.5" />
                    <span>{item.locations.join(', ')}</span>
                  </div>
                )}

                <div className="flex items-center gap-4 text-slate-400 text-sm">
                  {item.date && (
                    <div className="flex items-center gap-2">
                      <Calendar size={16} />
                      <span>{new Date(item.date).toLocaleDateString()}</span>
                    </div>
                  )}

                  {item.source && (
                    <div className="flex items-center gap-2">
                      <ExternalLink size={16} />
                      <span className="font-medium">{item.source}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
