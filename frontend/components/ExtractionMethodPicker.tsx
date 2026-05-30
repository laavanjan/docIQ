"use client";

import type { ExtractionMethod } from "@/lib/types";

interface Option {
  value: ExtractionMethod;
  label: string;
  description: string;
}

const OPTIONS: Option[] = [
  {
    value: "text",
    label: "Text",
    description: "Fast extraction for digital PDFs with selectable text (PyMuPDF).",
  },
  {
    value: "ocr",
    label: "OCR",
    description: "Scanned pages — YOLO layout detection + Tesseract OCR (needs poppler).",
  },
  {
    value: "vision",
    label: "Vision (Claude)",
    description: "Send page images to the LLM. Best for complex layouts, charts and scans.",
  },
];

interface Props {
  value: ExtractionMethod;
  onChange: (value: ExtractionMethod) => void;
  disabled?: boolean;
}

export default function ExtractionMethodPicker({ value, onChange, disabled }: Props) {
  return (
    <fieldset disabled={disabled} className="space-y-2">
      <legend className="mb-1 text-sm font-medium text-slate-700">Extraction method</legend>
      <div className="grid gap-2 sm:grid-cols-3">
        {OPTIONS.map((opt) => {
          const selected = value === opt.value;
          return (
            <label
              key={opt.value}
              className={`flex cursor-pointer flex-col rounded-lg border p-3 text-sm transition ${
                selected
                  ? "border-brand-600 bg-brand-50 ring-1 ring-brand-600"
                  : "border-slate-200 hover:border-slate-300"
              } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
            >
              <span className="flex items-center justify-between font-medium text-slate-800">
                {opt.label}
                <input
                  type="radio"
                  name="extraction-method"
                  value={opt.value}
                  checked={selected}
                  onChange={() => onChange(opt.value)}
                  className="h-4 w-4 accent-brand-600"
                />
              </span>
              <span className="mt-1 text-xs leading-snug text-slate-500">{opt.description}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
