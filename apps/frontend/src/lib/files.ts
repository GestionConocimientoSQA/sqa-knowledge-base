/**
 * Helpers para presentación de archivos.
 * Aislados acá para reusar desde uploader, chip, artifact card y futuras vistas.
 */
import {
  File as FileIcon,
  FileText,
  FileSpreadsheet,
  Presentation,
  type LucideIcon,
} from "lucide-react";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function extensionFromFilename(filename: string): string {
  if (!filename.includes(".")) return "";
  return filename.split(".").pop()!.toLowerCase();
}

export function iconForFile(filename: string): LucideIcon {
  const ext = extensionFromFilename(filename);
  switch (ext) {
    case "pdf":
    case "doc":
    case "docx":
    case "md":
    case "txt":
      return FileText;
    case "xls":
    case "xlsx":
    case "csv":
      return FileSpreadsheet;
    case "ppt":
    case "pptx":
      return Presentation;
    default:
      return FileIcon;
  }
}
