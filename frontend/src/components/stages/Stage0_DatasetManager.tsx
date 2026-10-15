import React, { useState, useEffect } from "react";
import {
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  Play,
  Columns,
  TableProperties,
  Calendar,
  Sparkles,
  BookOpen,
  Table,
  Upload,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { DatasetSummary, DatasetDetail, ExtractedDocument } from "../../types";
import { api } from "../../services/api";

interface Props {
  datasets: DatasetSummary[];
  selectedDataset: DatasetDetail | null;
  onSelectDatasetId: (id: string) => void;
  targetCol: string;
  setTargetCol: (val: string) => void;
  dateCol: string;
  setDateCol: (val: string) => void;
  onRunPipeline: () => void;
  isRunningPipeline: boolean;
  onOpenUploadModal?: () => void;
}

/* ---------- Helpers ---------- */

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600";

const plural = (n: number, word: string) =>
  `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;

const getFileKind = (filename: string) => {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "pdf":
      return {
        label: "PDF",
        icon: FileText,
        tile: "bg-rose-50 border-rose-100 text-rose-600",
      };
    case "docx":
      return {
        label: "DOCX",
        icon: FileText,
        tile: "bg-blue-50 border-blue-100 text-blue-600",
      };
    case "xlsx":
    case "xls":
      return {
        label: ext.toUpperCase(),
        icon: FileSpreadsheet,
        tile: "bg-emerald-50 border-emerald-100 text-emerald-600",
      };
    case "txt":
      return {
        label: "TXT",
        icon: FileText,
        tile: "bg-slate-100 border-slate-200 text-slate-600",
      };
    default:
      return {
        label: "CSV",
        icon: FileSpreadsheet,
        tile: "bg-indigo-50 border-indigo-100 text-indigo-600",
      };
  }
};

const getSizeLabel = (ds: {
  filename: string;
  row_count: number;
  column_count: number;
}) => {
  const name = ds.filename.toLowerCase();
  if (name.endsWith(".pdf")) return plural(ds.column_count, "page");
  if (name.endsWith(".docx")) return plural(ds.column_count, "section");
  return plural(ds.row_count, "row");
};

const humanize = (value: string) => {
  const text = value.replace(/_/g, " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const typeBadgeClass = (type: string) => {
  switch (type) {
    case "numeric":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "datetime":
      return "bg-purple-50 text-purple-700 border-purple-200";
    case "identifier":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-blue-50 text-blue-700 border-blue-200";
  }
};

const Stat: React.FC<{
  label: string;
  value: string | number;
  warn?: boolean;
}> = ({ label, value, warn }) => (
  <div
    className={`rounded-lg border px-4 py-3 ${warn ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-slate-50"}`}
  >
    <div className="text-xs text-slate-600">{label}</div>
    <div
      className={`mt-0.5 text-lg font-bold tabular-nums ${warn ? "text-amber-700" : "text-slate-900"}`}
    >
      {typeof value === "number" ? value.toLocaleString() : value}
    </div>
  </div>
);

/* ---------- Component ---------- */

export const Stage0_DatasetManager: React.FC<Props> = ({
  datasets,
  selectedDataset,
  onSelectDatasetId,
  targetCol,
  setTargetCol,
  dateCol,
  setDateCol,
  onRunPipeline,
  isRunningPipeline,
  onOpenUploadModal,
}) => {
  const [extractedDoc, setExtractedDoc] = useState<ExtractedDocument | null>(
    null,
  );
  const [docTab, setDocTab] = useState<"tables" | "paragraphs" | "evidence">(
    "tables",
  );
  const [loadingDoc, setLoadingDoc] = useState<boolean>(false);

  const isDocument =
    !!selectedDataset && /\.(pdf|docx)$/i.test(selectedDataset.filename);

  useEffect(() => {
    setExtractedDoc(null);
    if (!selectedDataset || !isDocument) return;

    let cancelled = false;
    setLoadingDoc(true);
    api
      .getExtractedDocument(selectedDataset.id)
      .then((doc) => {
        if (!cancelled) setExtractedDoc(doc);
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setLoadingDoc(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDataset?.id, isDocument]);

  const columns = selectedDataset?.schema_metadata.columns ?? [];
  const numericCount = columns.filter(
    (c) => c.inferred_type === "numeric",
  ).length;
  const needsAttentionCount = columns.filter(
    (c) => c.null_percentage > 5,
  ).length;
  const numericCandidates =
    selectedDataset?.schema_metadata.numeric_candidates ?? [];

  const docTabs = [
    {
      id: "tables",
      label: "Tables",
      icon: Table,
      count: extractedDoc?.tables.length ?? 0,
    },
    {
      id: "evidence",
      label: "Evidence",
      icon: Sparkles,
      count: extractedDoc?.evidence_items.length ?? 0,
    },
    {
      id: "paragraphs",
      label: "Paragraphs",
      icon: BookOpen,
      count: extractedDoc?.paragraphs.length ?? 0,
    },
  ] as const;

  const selectClass = `w-full text-sm bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-slate-900 hover:border-slate-400 motion-safe:transition-colors cursor-pointer ${focusRing}`;

  return (
    <div className="space-y-8">
      {/* Top Banner: Data Upload */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-sm border border-slate-800">
        <div className="max-w-3xl">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white mb-2">
            Start Your Business Analysis
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed">
            Upload business datasets and reports to uncover findings, supporting
            evidence, and actionable insights.
          </p>
        </div>
      </div>

      {/* File picker */}
      <section className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Choose a file</h2>
            <p className="mt-0.5 text-sm text-slate-600">
              {plural(datasets.length, "file")} available. Select one to review
              its structure and set up the analysis.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            {onOpenUploadModal && (
              <button
                type="button"
                onClick={onOpenUploadModal}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-sm motion-safe:transition-colors cursor-pointer ${focusRing}`}
              >
                <Upload className="w-4 h-4" />
                <span>Upload file</span>
              </button>
            )}
          </div>
        </div>

        {datasets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center space-y-3">
            <FileSpreadsheet className="w-8 h-8 text-slate-400 mx-auto" />
            <div>
              <p className="text-base font-semibold text-slate-800">
                No files yet
              </p>
              <p className="text-sm text-slate-600">
                Upload a dataset or report to begin.
              </p>
            </div>
            {onOpenUploadModal && (
              <button
                type="button"
                onClick={onOpenUploadModal}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 motion-safe:transition-colors cursor-pointer ${focusRing}`}
              >
                <Upload className="w-4 h-4" />
                <span>Upload file</span>
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {datasets.map((ds) => {
              const isSelected = selectedDataset?.id === ds.id;
              const kind = getFileKind(ds.filename);
              const Icon = kind.icon;
              return (
                <button
                  key={ds.id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => onSelectDatasetId(ds.id)}
                  className={`text-left rounded-xl border p-4 flex gap-3.5 motion-safe:transition cursor-pointer ${focusRing} ${
                    isSelected
                      ? "border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs"
                  }`}
                >
                  <div
                    className={`w-11 h-11 shrink-0 rounded-xl border flex items-center justify-center ${kind.tile}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h3
                        className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2"
                        title={ds.name}
                      >
                        {ds.name}
                      </h3>
                      {isSelected && (
                        <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                      )}
                    </div>
                    <p
                      className="mt-1 text-xs text-slate-500 truncate"
                      title={ds.filename}
                    >
                      {ds.filename}
                    </p>
                    <div className="mt-2.5 flex items-center gap-2 text-xs text-slate-600">
                      <span className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-semibold">
                        {kind.label}
                      </span>
                      <span>{getSizeLabel(ds)}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Nothing selected yet */}
      {!selectedDataset && datasets.length > 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center text-sm text-slate-600">
          Select a file above to see its structure and set up the analysis.
        </div>
      )}

      {/* Selected dataset */}
      {selectedDataset && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Setup card */}
          <section className="lg:col-span-1 bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs flex flex-col gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
                <TableProperties className="w-4 h-4" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">
                {isDocument ? "Document profile" : "Analysis setup"}
              </h2>
            </div>

            <dl className="rounded-xl bg-slate-50 border border-slate-200 divide-y divide-slate-200 text-sm">
              <div className="flex items-start justify-between gap-4 px-4 py-3">
                <dt className="text-slate-600 shrink-0">File</dt>
                <dd className="font-medium text-slate-900 text-right break-all">
                  {selectedDataset.filename}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4 px-4 py-3">
                <dt className="text-slate-600 shrink-0">Format</dt>
                <dd className="font-medium text-slate-900 text-right">
                  {(
                    selectedDataset.schema_metadata.format || "CSV"
                  ).toUpperCase()}
                  {" · "}
                  {humanize(
                    selectedDataset.schema_metadata.file_type || "structured",
                  )}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4 px-4 py-3">
                <dt className="text-slate-600 shrink-0">Size</dt>
                <dd className="font-medium text-slate-900 text-right">
                  {isDocument
                    ? `${plural(selectedDataset.row_count, "paragraph")} · ${plural(selectedDataset.column_count, /\.pdf$/i.test(selectedDataset.filename) ? "page" : "section")}`
                    : `${plural(selectedDataset.row_count, "row")} × ${plural(selectedDataset.column_count, "column")}`}
                </dd>
              </div>
            </dl>

            {!isDocument ? (
              <div className="flex flex-col flex-1 gap-5">
                <div>
                  <label
                    htmlFor="primary-metric"
                    className="block text-sm font-semibold text-slate-800 mb-1.5"
                  >
                    Primary metric
                  </label>
                  {numericCandidates.length === 0 ? (
                    <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>
                        No numeric columns were found, so there is no metric to
                        analyze in this file.
                      </span>
                    </div>
                  ) : (
                    <>
                      <select
                        id="primary-metric"
                        value={targetCol}
                        onChange={(e) => setTargetCol(e.target.value)}
                        className={selectClass}
                      >
                        {numericCandidates.map((col) => (
                          <option key={col} value={col}>
                            {col}
                            {col ===
                            selectedDataset.schema_metadata.suggested_target
                              ? " (suggested)"
                              : ""}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1.5 text-xs text-slate-500">
                        The measure your analysis will focus on.
                      </p>
                    </>
                  )}
                </div>

                <div>
                  <label
                    htmlFor="date-column"
                    className="flex items-center gap-1.5 text-sm font-semibold text-slate-800 mb-1.5"
                  >
                    <Calendar className="w-4 h-4 text-slate-400" />
                    Date column{" "}
                    <span className="font-normal text-slate-500">
                      (optional)
                    </span>
                  </label>
                  <select
                    id="date-column"
                    value={dateCol}
                    onChange={(e) => setDateCol(e.target.value)}
                    className={selectClass}
                  >
                    <option value="">None (split at midpoint)</option>
                    {selectedDataset.schema_metadata.datetime_candidates.map(
                      (col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ),
                    )}
                  </select>
                  <p className="mt-1.5 text-xs text-slate-500">
                    Used to compare earlier and later periods. Without one, the
                    data is split in the middle.
                  </p>
                </div>

                {targetCol && (
                  <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 space-y-2.5">
                    <p className="text-sm font-semibold text-slate-900">
                      What will run
                    </p>
                    <ul className="space-y-2 text-sm text-slate-700">
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        <span>
                          Analyze <b className="text-slate-900">{targetCol}</b>{" "}
                          across {plural(selectedDataset.row_count, "row")}
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        <span>
                          {dateCol ? (
                            <>
                              Compare periods using{" "}
                              <b className="text-slate-900">{dateCol}</b>
                            </>
                          ) : (
                            "Compare the first and second half of the data"
                          )}
                        </span>
                      </li>
                    </ul>
                  </div>
                )}

                <div className="mt-auto pt-1">
                  <button
                    type="button"
                    onClick={onRunPipeline}
                    disabled={isRunningPipeline || !targetCol}
                    className={`w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-semibold text-white shadow-sm motion-safe:transition-colors ${focusRing} ${
                      isRunningPipeline
                        ? "bg-blue-400 cursor-wait"
                        : "bg-blue-600 hover:bg-blue-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    }`}
                  >
                    {isRunningPipeline ? (
                      <>
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        <span>Running analysis...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" />
                        <span>Run analysis</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col flex-1 gap-4">
                <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl space-y-1.5">
                  <div className="text-sm font-bold text-purple-900">
                    Business document processed
                  </div>
                  <p className="text-sm text-purple-900/90 leading-relaxed">
                    This document has been parsed into structured evidence,
                    including page numbers, section headers, and extracted
                    tables. Review the extracted content on the right.
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* Right panel */}
          <section className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs flex flex-col gap-5">
            {!isDocument ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
                      <Columns className="w-4 h-4" />
                    </div>
                    <h2 className="text-lg font-bold text-slate-900">
                      Data structure and profile
                    </h2>
                  </div>
                  <span className="text-sm text-slate-600">
                    {plural(columns.length, "column")} identified
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <Stat label="Rows" value={selectedDataset.row_count} />
                  <Stat label="Columns" value={selectedDataset.column_count} />
                  <Stat label="Numeric" value={numericCount} />
                  <Stat
                    label="Over 5% missing"
                    value={needsAttentionCount}
                    warn={needsAttentionCount > 0}
                  />
                </div>

                <div className="overflow-auto max-h-[28rem] border border-slate-200 rounded-xl">
                  <table className="w-full table-fixed text-left text-sm text-slate-700">
                    <colgroup>
                      <col className="w-[27%]" />
                      <col className="w-[17%]" />
                      <col className="w-[13%]" />
                      <col className="w-[13%]" />
                      <col className="w-[30%]" />
                    </colgroup>
                    <thead className="sticky top-0 z-10 bg-slate-50 text-xs font-semibold text-slate-600 border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-3">Column</th>
                        <th className="py-3 px-3">Type</th>
                        <th className="py-3 px-3">Missing</th>
                        <th className="py-3 px-3">Unique</th>
                        <th className="py-3 px-3">Range or sample</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {columns.map((col) => (
                        <tr key={col.name} className="hover:bg-slate-50/70">
                          <td
                            className="py-2.5 px-3 font-semibold text-slate-900 truncate"
                            title={col.name}
                          >
                            {col.name}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded-md text-xs font-semibold capitalize border ${typeBadgeClass(
                                col.inferred_type,
                              )}`}
                            >
                              {col.inferred_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 tabular-nums">
                            <span
                              className={
                                col.null_percentage > 5
                                  ? "text-amber-700 font-semibold"
                                  : "text-slate-600"
                              }
                            >
                              {col.null_percentage}%
                            </span>
                          </td>
                          <td className="py-2.5 px-3 tabular-nums text-slate-600">
                            {col.unique_count.toLocaleString()}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600 font-mono text-xs">
                            {(() => {
                              const text =
                                col.min_val !== null && col.max_val !== null
                                  ? `${col.min_val} to ${col.max_val}`
                                  : (col.sample_values
                                      ?.slice(0, 3)
                                      .join(", ") ?? "");
                              return (
                                <span className="block truncate" title={text}>
                                  {text}
                                </span>
                              );
                            })()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="space-y-5">
                <div
                  role="tablist"
                  aria-label="Extracted document content"
                  className="flex flex-wrap gap-2 border-b border-slate-200 pb-4"
                >
                  {docTabs.map(({ id, label, icon: TabIcon, count }) => {
                    const active = docTab === id;
                    return (
                      <button
                        key={id}
                        role="tab"
                        type="button"
                        aria-selected={active}
                        onClick={() => setDocTab(id)}
                        className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold motion-safe:transition-colors cursor-pointer ${focusRing} ${
                          active
                            ? "bg-purple-50 text-purple-700 border border-purple-200"
                            : "text-slate-600 border border-transparent hover:bg-slate-100"
                        }`}
                      >
                        <TabIcon className="w-4 h-4" />
                        <span>{label}</span>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded-full ${active ? "bg-purple-100" : "bg-slate-100"}`}
                        >
                          {count}
                        </span>
                      </button>
                    );
                  })}
                </div>

                {loadingDoc ? (
                  <div className="py-14 text-center text-sm text-slate-600 motion-safe:animate-pulse">
                    Extracting document structure, pages, and tables...
                  </div>
                ) : extractedDoc ? (
                  <div
                    role="tabpanel"
                    className="max-h-[28rem] overflow-y-auto space-y-4 pr-1"
                  >
                    {docTab === "tables" && (
                      <div className="space-y-4">
                        {extractedDoc.tables.length === 0 ? (
                          <p className="text-sm text-slate-600 p-4 bg-slate-50 rounded-lg">
                            No tables were detected in this document.
                          </p>
                        ) : (
                          extractedDoc.tables.map((tbl, tIdx) => (
                            <div
                              key={tIdx}
                              className="border border-slate-200 rounded-xl overflow-hidden"
                            >
                              <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between gap-3">
                                <span className="text-sm font-semibold text-slate-900">
                                  {tbl.caption || `Table ${tIdx + 1}`}
                                </span>
                                <span className="text-xs text-slate-600 shrink-0">
                                  {tbl.row_count} rows × {tbl.col_count} columns
                                </span>
                              </div>
                              <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm text-slate-700">
                                  <thead className="bg-slate-100/70 border-b border-slate-200 text-xs font-semibold text-slate-800">
                                    <tr>
                                      {tbl.headers.map((h, hIdx) => (
                                        <th key={hIdx} className="py-2.5 px-4">
                                          {h}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100">
                                    {tbl.rows.map((r, rIdx) => (
                                      <tr
                                        key={rIdx}
                                        className="hover:bg-slate-50/70"
                                      >
                                        {r.map((cell, cIdx) => (
                                          <td
                                            key={cIdx}
                                            className="py-2.5 px-4"
                                          >
                                            {String(cell)}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {docTab === "evidence" && (
                      <div className="space-y-3">
                        {extractedDoc.evidence_items.map((evid, eIdx) => (
                          <div
                            key={eIdx}
                            className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-bold text-slate-900">
                                {evid.metric_name || "Metric extract"}
                              </span>
                              <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-purple-100 text-purple-800 shrink-0">
                                {evid.location.page_number
                                  ? `Page ${evid.location.page_number}`
                                  : evid.location.heading_or_section ||
                                    "Document"}
                              </span>
                            </div>
                            <p className="text-sm text-slate-700 italic">
                              “{evid.content}”
                            </p>
                            {evid.metric_value !== null &&
                              evid.metric_value !== undefined && (
                                <div className="text-sm font-mono font-semibold text-blue-700">
                                  Disclosed value: {evid.unit}
                                  {evid.metric_value.toLocaleString()}
                                </div>
                              )}
                          </div>
                        ))}
                      </div>
                    )}

                    {docTab === "paragraphs" && (
                      <div className="space-y-3">
                        {extractedDoc.paragraphs.map((para, pIdx) => (
                          <div
                            key={pIdx}
                            className="p-4 bg-slate-50/80 border border-slate-200 rounded-xl space-y-1.5"
                          >
                            <div className="text-xs font-semibold text-slate-600">
                              {para.page
                                ? `Page ${para.page}`
                                : para.section || "Paragraph"}
                            </div>
                            <p className="text-sm text-slate-800 leading-relaxed">
                              {para.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
};
