import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Upload,
  CheckCircle2,
  AlertCircle,
  FileText,
  FileSpreadsheet,
  Loader2,
} from 'lucide-react';
import { api } from '../../services/api';
import { DatasetDetail } from '../../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onDatasetUploaded: (dataset: DatasetDetail) => void;
}

const VALID_EXTENSIONS = ['.csv', '.txt', '.xlsx', '.xls', '.pdf', '.docx'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

const SUPPORTED_FILES = [
  { icon: FileSpreadsheet, label: 'Spreadsheets', ext: '.csv, .xlsx, .xls' },
  { icon: FileText, label: 'Documents', ext: '.pdf, .docx' },
  { icon: FileText, label: 'Plain text', ext: '.txt' },
];

const NEXT_STEPS = [
  'Your columns are profiled automatically.',
  'A data quality check is run on the file.',
  'Baseline health and key metrics are calculated.',
];

const formatSize = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(1)} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

const isSpreadsheet = (name: string) => /\.(csv|xlsx|xls)$/i.test(name);

const focusRing =
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';

export const UploadModal: React.FC<Props> = ({ isOpen, onClose, onDatasetUploaded }) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const requestClose = () => {
    if (!isUploading) onClose();
  };

  // Reset state, lock page scroll, and manage focus while the modal is open.
  // (Hooks now run before the early return below, so the Rules of Hooks are respected.)
  useEffect(() => {
    if (!isOpen) return;

    setSelectedFile(null);
    setErrorMsg(null);
    setDragActive(false);
    setIsUploading(false);

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [isOpen]);

  // Close on Escape (unless an upload is in progress).
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isUploading) onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isOpen, isUploading, onClose]);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      // Ignore dragleave events fired when moving over child elements.
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
        setDragActive(false);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMsg(null);
    const hasValidExt = VALID_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      setErrorMsg('Unsupported file type. Please upload a CSV, Excel, PDF, or Word file.');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setErrorMsg('This file is larger than the 50 MB limit.');
      return;
    }
    setSelectedFile(file);
  };

  const clearFile = () => {
    setSelectedFile(null);
    setErrorMsg(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setErrorMsg(null);
    try {
      const dataset = await api.uploadDataset(selectedFile);
      onDatasetUploaded(dataset);
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Dataset upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const FileIcon = selectedFile && isSpreadsheet(selectedFile.name) ? FileSpreadsheet : FileText;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) requestClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
        aria-describedby="upload-modal-desc"
        tabIndex={-1}
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-white rounded-xl shadow-2xl border border-slate-200 outline-none motion-safe:animate-fade-in"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-5">
          <div className="flex items-start gap-3">
            <div className="w-11 h-11 shrink-0 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 id="upload-modal-title" className="text-lg font-bold text-slate-900">
                Upload your data
              </h2>
              <p id="upload-modal-desc" className="mt-0.5 text-sm text-slate-600">
                Add a business dataset or document to start your analysis.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={requestClose}
            disabled={isUploading}
            aria-label="Close upload dialog"
            className={`p-1.5 -mr-1.5 -mt-1 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg motion-safe:transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${focusRing}`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="grid md:grid-cols-5 border-t border-slate-100">
          <div className="md:col-span-3 px-6 py-6 space-y-4">
            {errorMsg && (
              <div
                role="alert"
                className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700 flex items-start gap-2"
              >
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Hidden native input, shared by the dropzone and the "change file" action */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt,.xlsx,.xls,.pdf,.docx"
              onChange={handleChange}
              className="hidden"
            />

            {selectedFile ? (
              /* Selected file card */
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 shrink-0 rounded-xl bg-white border border-emerald-200 text-emerald-600 flex items-center justify-center">
                    <FileIcon className="w-5 h-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900" title={selectedFile.name}>
                      {selectedFile.name}
                    </p>
                    <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-600">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Ready to upload ({formatSize(selectedFile.size)})</span>
                    </p>
                  </div>
                  {!isUploading && (
                    <button
                      type="button"
                      onClick={clearFile}
                      aria-label="Remove selected file"
                      className={`p-1.5 text-slate-500 hover:text-rose-600 hover:bg-white rounded-lg motion-safe:transition-colors cursor-pointer ${focusRing}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {isUploading && (
                  <div role="status" className="space-y-1.5">
                    <div className="h-1.5 rounded-full bg-blue-100 overflow-hidden">
                      <div className="h-full w-full rounded-full bg-blue-600 motion-safe:animate-pulse" />
                    </div>
                    <p className="text-xs text-slate-600">Uploading and profiling your file...</p>
                  </div>
                )}
              </div>
            ) : (
              /* Dropzone */
              <div
                role="button"
                tabIndex={0}
                aria-label="Choose a file to upload"
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                className={`min-h-[17rem] flex items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center cursor-pointer motion-safe:transition-colors ${focusRing} ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-slate-300 bg-slate-50/60 hover:border-blue-400 hover:bg-blue-50/40'
                }`}
              >
                <div className="flex flex-col items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center motion-safe:transition-colors ${
                      dragActive ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-blue-600'
                    }`}
                  >
                    <Upload className="w-5 h-5" />
                  </div>

                  <div className="space-y-1">
                    <p className="text-sm text-slate-700">
                      {dragActive ? (
                        <span className="font-semibold text-blue-700">Drop your file to select it</span>
                      ) : (
                        <>
                          Drag and drop a file here, or{' '}
                          <span className="font-semibold text-blue-600 underline underline-offset-2">browse</span>
                        </>
                      )}
                    </p>
                    <p className="text-xs text-slate-500">Up to 50 MB</p>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* Side panel: supported files and what happens next */}
          <aside className="md:col-span-2 bg-slate-50 border-t md:border-t-0 md:border-l border-slate-100 px-6 py-6 space-y-7">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Supported files</h3>
              <ul className="mt-3 space-y-2.5">
                {SUPPORTED_FILES.map(({ icon: Icon, label, ext }) => (
                  <li key={label} className="flex items-center gap-3 text-sm">
                    <span className="w-8 h-8 shrink-0 rounded-lg bg-white border border-slate-200 text-slate-500 flex items-center justify-center">
                      <Icon className="w-4 h-4" />
                    </span>
                    <span>
                      <span className="font-medium text-slate-900">{label}</span>{' '}
                      <span className="text-slate-500">{ext}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-500">Maximum file size is 50 MB.</p>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-900">What happens next</h3>
              <ol className="mt-3 space-y-3">
                {NEXT_STEPS.map((text, i) => (
                  <li key={text} className="flex items-start gap-3 text-sm text-slate-700">
                    <span className="w-6 h-6 shrink-0 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="pt-0.5">{text}</span>
                  </li>
                ))}
              </ol>
            </div>
          </aside>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 bg-white border-t border-slate-200 rounded-b-xl">
          <button
            type="button"
            onClick={requestClose}
            disabled={isUploading}
            className={`px-4 py-2.5 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-200/70 motion-safe:transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${focusRing}`}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleUploadSubmit}
            disabled={!selectedFile || isUploading}
            className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-sm motion-safe:transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${focusRing}`}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                <span>Uploading...</span>
              </>
            ) : (
              <span>Upload and profile</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};