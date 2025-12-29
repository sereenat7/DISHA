import { Bell, Settings, User } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700 shadow-lg">
      <div className="px-8 py-5 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white">{title}</h2>
          {subtitle && <p className="text-slate-400 mt-1">{subtitle}</p>}
        </div>

        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors relative group">
            <Bell size={20} className="text-slate-300 group-hover:text-white transition-colors" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors group">
            <Settings size={20} className="text-slate-300 group-hover:text-white transition-colors" />
          </button>

          <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/20">
            <User size={18} className="text-white" />
            <span className="text-white font-medium">Admin</span>
          </button>
        </div>
      </div>
    </header>
  );
}
