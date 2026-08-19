import React, { useState, useEffect } from 'react';
import {
  FolderIcon,
  FilmIcon,
  ChevronRightIcon,
  ArrowUpIcon,
  XMarkIcon,
  CheckIcon,
  MagnifyingGlassIcon,
  ComputerDesktopIcon,
  FolderArrowDownIcon,
  DocumentDuplicateIcon,
  HomeIcon
} from '@heroicons/react/24/outline';

interface FileItem {
  name: string;
  path: string;
  size?: string;
}

interface DirResponse {
  current_path: string;
  parent_path: string;
  drives: string[];
  folders: FileItem[];
  files: FileItem[];
  error?: string;
}

interface FileExplorerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (selectedPath: string) => void;
  initialPath?: string;
}

export const FileExplorerModal: React.FC<FileExplorerModalProps> = ({
  isOpen,
  onClose,
  onSelect,
  initialPath = ''
}) => {
  const [currentPath, setCurrentPath] = useState<string>('');
  const [parentPath, setParentPath] = useState<string>('');
  const [drives, setDrives] = useState<string[]>([]);
  const [folders, setFolders] = useState<FileItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedItem, setSelectedItem] = useState<{ path: string; type: 'folder' | 'file' } | null>(null);
  const [manualPath, setManualPath] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadDirectory = async (path: string = '') => {
    setLoading(true);
    setError(null);
    setSelectedItem(null);
    try {
      const res = await fetch(`/api/list-dir?path=${encodeURIComponent(path)}`);
      const data: DirResponse = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setCurrentPath(data.current_path);
        setManualPath(data.current_path);
        setParentPath(data.parent_path);
        setDrives(data.drives || []);
        setFolders(data.folders || []);
        setFiles(data.files || []);
      }
    } catch (err: any) {
      setError(err.message || 'Gagal memuat direktori');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadDirectory(initialPath);
    }
  }, [isOpen, initialPath]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (!selectedItem) {
      if (currentPath) {
        onSelect(currentPath);
        onClose();
      }
      return;
    }
    if (selectedItem.type === 'file') {
      onSelect(selectedItem.path);
      onClose();
    } else {
      loadDirectory(selectedItem.path);
    }
  };

  const filteredFolders = folders.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase()));
  const filteredFiles = files.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div 
        className="flex h-[82vh] w-full max-w-4xl flex-col rounded-2xl border border-slate-800 bg-[#0d1117] text-slate-100 shadow-2xl overflow-hidden font-['Instrument_Sans',_sans-serif]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex h-14 items-center justify-between border-b border-slate-800/80 bg-[#161b22] px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
              <FolderIcon className="h-4 w-4 stroke-[2]" />
            </div>
            <div>
              <h2 className="font-['Outfit'] text-sm font-bold text-white">
                Pilih File Video
              </h2>
              <p className="text-[11px] text-slate-400">
                Pilih file video (.mp4, .mov, .mkv, .webm) untuk diproses
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <XMarkIcon className="h-5 w-5 stroke-[2]" />
          </button>
        </div>

        {/* Path Navigation Bar */}
        <div className="flex items-center gap-2 border-b border-slate-800/80 bg-[#0f141b] px-4 py-2.5">
          <button
            onClick={() => parentPath && loadDirectory(parentPath)}
            disabled={!parentPath || loading}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-xs"
            title="Ke Folder Atas (Parent Directory)"
          >
            <ArrowUpIcon className="h-4 w-4 stroke-[2]" />
          </button>

          <div className="relative flex-1">
            <input
              type="text"
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadDirectory(manualPath)}
              placeholder="/path/to/folder..."
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 font-mono text-xs text-emerald-300 focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <button
            onClick={() => loadDirectory(manualPath)}
            disabled={loading}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 hover:text-white transition-all shadow-xs"
          >
            Go
          </button>

          {/* Quick Filter Search */}
          <div className="relative w-48 hidden sm:block">
            <MagnifyingGlassIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari file..."
              className="w-full rounded-lg border border-slate-800 bg-slate-950 pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Main Content Area: Sidebar + Grid */}
        <div className="flex flex-1 overflow-hidden">
          
          {/* Left Sidebar: Quick Access & Drives */}
          <aside className="w-52 flex-shrink-0 border-r border-slate-800/80 bg-[#0e1218] p-3 space-y-4 overflow-y-auto">
            
            {/* Quick Access */}
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2">
                Quick Access
              </span>
              <div className="mt-1.5 space-y-1">
                <button
                  onClick={() => loadDirectory('')}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                >
                  <HomeIcon className="h-4 w-4 text-emerald-400 stroke-[2]" />
                  <span>Home</span>
                </button>
                <button
                  onClick={() => loadDirectory(`${currentPath.split('/')[0] || ''}/Users/${currentPath.split('/')[2] || 'user'}/Desktop`)}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                >
                  <ComputerDesktopIcon className="h-4 w-4 text-sky-400 stroke-[2]" />
                  <span>Desktop</span>
                </button>
                <button
                  onClick={() => loadDirectory(`${currentPath.split('/')[0] || ''}/Users/${currentPath.split('/')[2] || 'user'}/Downloads`)}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                >
                  <FolderArrowDownIcon className="h-4 w-4 text-amber-400 stroke-[2]" />
                  <span>Downloads</span>
                </button>
                <button
                  onClick={() => loadDirectory(`${currentPath.split('/')[0] || ''}/Users/${currentPath.split('/')[2] || 'user'}/Documents`)}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                >
                  <DocumentDuplicateIcon className="h-4 w-4 text-purple-400 stroke-[2]" />
                  <span>Documents</span>
                </button>
              </div>
            </div>

            {/* Drives */}
            {drives.length > 0 && (
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2">
                  Drives
                </span>
                <div className="mt-1.5 space-y-1">
                  {drives.map((drive) => (
                    <button
                      key={drive}
                      onClick={() => loadDirectory(drive)}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                    >
                      <span className="font-mono text-emerald-400 font-bold">💾 {drive}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

          </aside>

          {/* Right Explorer Grid */}
          <main className="flex-1 overflow-y-auto p-4 scrollbar-thin">
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center text-slate-400">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent mb-2" />
                <span className="text-xs">Memuat file & folder...</span>
              </div>
            ) : error ? (
              <div className="flex h-full flex-col items-center justify-center text-rose-400 p-4 text-center">
                <span className="text-2xl mb-1">⚠️</span>
                <span className="text-xs font-semibold">{error}</span>
                <button
                  onClick={() => loadDirectory('')}
                  className="mt-3 rounded-lg bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
                >
                  Kembali ke Home
                </button>
              </div>
            ) : filteredFolders.length === 0 && filteredFiles.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-slate-500">
                <FolderIcon className="h-10 w-10 stroke-[1.5] mb-2 opacity-40" />
                <span className="text-xs">Tidak ada folder atau file video di sini</span>
              </div>
            ) : (
              <div className="space-y-4">
                
                {/* Folders List */}
                {filteredFolders.length > 0 && (
                  <div>
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                      Folders ({filteredFolders.length})
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1.5">
                      {filteredFolders.map((folder) => {
                        const isSelected = selectedItem?.path === folder.path;
                        return (
                          <div
                            key={folder.path}
                            onClick={() => setSelectedItem({ path: folder.path, type: 'folder' })}
                            onDoubleClick={() => loadDirectory(folder.path)}
                            className={`flex items-center gap-2.5 rounded-xl border p-2 text-xs transition-all cursor-pointer select-none ${
                              isSelected
                                ? 'border-emerald-500 bg-emerald-950/40 text-white ring-1 ring-emerald-500/40 shadow-xs'
                                : 'border-slate-800/80 bg-slate-900/50 text-slate-300 hover:bg-slate-850 hover:border-slate-700'
                            }`}
                          >
                            <FolderIcon className="h-4 w-4 text-amber-400 flex-shrink-0 stroke-[2]" />
                            <span className="truncate flex-1 font-medium">{folder.name}</span>
                            <ChevronRightIcon className="h-3 w-3 text-slate-600 flex-shrink-0" />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Video Files List */}
                {filteredFiles.length > 0 && (
                  <div>
                    <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-2">
                      Video Files ({filteredFiles.length})
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {filteredFiles.map((file) => {
                        const isSelected = selectedItem?.path === file.path;
                        return (
                          <div
                            key={file.path}
                            onClick={() => setSelectedItem({ path: file.path, type: 'file' })}
                            onDoubleClick={() => {
                              onSelect(file.path);
                              onClose();
                            }}
                            className={`flex items-center justify-between rounded-xl border p-2.5 text-xs transition-all cursor-pointer select-none ${
                              isSelected
                                ? 'border-emerald-500 bg-emerald-950/50 text-white ring-2 ring-emerald-500/40 shadow-md'
                                : 'border-slate-800/90 bg-slate-900/80 text-slate-200 hover:bg-slate-800 hover:border-slate-700'
                            }`}
                          >
                            <div className="flex items-center gap-2.5 truncate min-w-0 pr-2">
                              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 flex-shrink-0">
                                <FilmIcon className="h-4 w-4 stroke-[2]" />
                              </div>
                              <span className="truncate font-semibold text-slate-100">{file.name}</span>
                            </div>
                            {file.size && (
                              <span className="rounded bg-slate-950 px-2 py-0.5 font-mono text-[10px] text-slate-400 border border-slate-800 flex-shrink-0">
                                {file.size}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              </div>
            )}
          </main>
        </div>

        {/* Modal Footer */}
        <div className="flex h-14 items-center justify-between border-t border-slate-800/80 bg-[#161b22] px-5">
          <div className="truncate text-xs font-mono text-slate-400 max-w-md">
            {selectedItem ? (
              <span>
                Pilihan: <strong className="text-emerald-400">{selectedItem.path}</strong>
              </span>
            ) : (
              <span>Pilih file video atau double click untuk membuka</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
            >
              Batal
            </button>
            <button
              onClick={handleConfirm}
              disabled={!selectedItem}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 text-xs font-bold text-white transition-all shadow-md active:scale-95"
            >
              <CheckIcon className="h-4 w-4 stroke-[2.5]" />
              <span>Pilih Video Ini</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
