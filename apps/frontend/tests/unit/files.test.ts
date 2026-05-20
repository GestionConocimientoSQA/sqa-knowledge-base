import { describe, it, expect } from "vitest";
import {
  File as FileIcon,
  FileText,
  FileSpreadsheet,
  Presentation,
} from "lucide-react";
import {
  formatBytes,
  extensionFromFilename,
  iconForFile,
} from "@/lib/files";

describe("files helpers", () => {
  describe("formatBytes", () => {
    it("formats bytes under 1KB as B", () => {
      expect(formatBytes(0)).toBe("0 B");
      expect(formatBytes(512)).toBe("512 B");
      expect(formatBytes(1023)).toBe("1023 B");
    });

    it("formats kilobytes with one decimal", () => {
      expect(formatBytes(1024)).toBe("1.0 KB");
      expect(formatBytes(2048)).toBe("2.0 KB");
      expect(formatBytes(1500)).toBe("1.5 KB");
    });

    it("formats megabytes with one decimal", () => {
      expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
      expect(formatBytes(2.5 * 1024 * 1024)).toBe("2.5 MB");
    });
  });

  describe("extensionFromFilename", () => {
    it("returns lowercase extension without dot", () => {
      expect(extensionFromFilename("plan.PDF")).toBe("pdf");
      expect(extensionFromFilename("Doc.DOCX")).toBe("docx");
    });

    it("returns empty string when no dot", () => {
      expect(extensionFromFilename("README")).toBe("");
    });

    it("takes only the final segment when filename has multiple dots", () => {
      expect(extensionFromFilename("a.b.c.md")).toBe("md");
    });
  });

  describe("iconForFile", () => {
    it("maps text-y formats to FileText", () => {
      expect(iconForFile("a.pdf")).toBe(FileText);
      expect(iconForFile("a.docx")).toBe(FileText);
      expect(iconForFile("a.doc")).toBe(FileText);
      expect(iconForFile("a.md")).toBe(FileText);
      expect(iconForFile("a.txt")).toBe(FileText);
    });

    it("maps spreadsheets to FileSpreadsheet", () => {
      expect(iconForFile("a.xlsx")).toBe(FileSpreadsheet);
      expect(iconForFile("a.xls")).toBe(FileSpreadsheet);
      expect(iconForFile("a.csv")).toBe(FileSpreadsheet);
    });

    it("maps presentations to Presentation icon", () => {
      expect(iconForFile("a.pptx")).toBe(Presentation);
      expect(iconForFile("a.ppt")).toBe(Presentation);
    });

    it("falls back to generic File icon for unknown extensions", () => {
      expect(iconForFile("noext")).toBe(FileIcon);
      expect(iconForFile("data.bin")).toBe(FileIcon);
    });
  });
});
