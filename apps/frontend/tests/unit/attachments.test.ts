import { describe, it, expect, beforeEach } from "vitest";
import {
  AttachmentValidationError,
  listAttachments,
  removeAttachment,
  uploadAttachment,
} from "@/lib/api/attachments";
import { attachmentsStore } from "@/lib/api/attachments-store";
import type { AttachmentMetadata } from "@/types/agent";

function makeFile(
  name: string,
  contentLength: number,
  type: string,
): File {
  const content = "x".repeat(contentLength);
  return new File([content], name, { type });
}

describe("attachments API (stub)", () => {
  beforeEach(() => {
    attachmentsStore.clear();
  });

  it("uploadAttachment reaches uploaded status with 100% progress", async () => {
    const file = makeFile("note.pdf", 32, "application/pdf");
    const result = await uploadAttachment({
      sessionId: "ses-1",
      file,
    });
    expect(result.status).toBe("uploaded");
    expect(result.progress).toBe(100);
    expect(result.blobPath).toContain("ses-1");
    expect(result.filename).toBe("note.pdf");
  });

  it("uploadAttachment emits progress updates monotonically", async () => {
    const file = makeFile("plan.docx", 16, "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    const progresses: number[] = [];
    await uploadAttachment({
      sessionId: "ses-1",
      file,
      onProgress: (meta) => progresses.push(meta.progress),
    });
    expect(progresses[0]).toBe(0);
    expect(progresses.at(-1)).toBe(100);
    for (let i = 1; i < progresses.length; i++) {
      expect(progresses[i]).toBeGreaterThanOrEqual(progresses[i - 1]!);
    }
  });

  it("uploadAttachment rejects oversized files", async () => {
    const file = makeFile("huge.pdf", 11 * 1024 * 1024, "application/pdf");
    await expect(
      uploadAttachment({ sessionId: "ses-1", file }),
    ).rejects.toBeInstanceOf(AttachmentValidationError);
  });

  it("uploadAttachment rejects unsupported MIME types", async () => {
    const file = makeFile("malware.exe", 100, "application/x-msdownload");
    await expect(
      uploadAttachment({ sessionId: "ses-1", file }),
    ).rejects.toBeInstanceOf(AttachmentValidationError);
  });

  it("uploadAttachment accepts files by extension when MIME is missing", async () => {
    const file = makeFile("plan.md", 50, "");
    const result = await uploadAttachment({ sessionId: "ses-1", file });
    expect(result.status).toBe("uploaded");
  });

  it("listAttachments scopes results by session", async () => {
    await uploadAttachment({
      sessionId: "ses-A",
      file: makeFile("a.pdf", 10, "application/pdf"),
    });
    await uploadAttachment({
      sessionId: "ses-B",
      file: makeFile("b.pdf", 10, "application/pdf"),
    });
    const aResults = await listAttachments("ses-A");
    expect(aResults).toHaveLength(1);
    expect(aResults[0]?.filename).toBe("a.pdf");
  });

  it("removeAttachment deletes only the requested attachment", async () => {
    const first = await uploadAttachment({
      sessionId: "ses-1",
      file: makeFile("first.pdf", 5, "application/pdf"),
    });
    const second = await uploadAttachment({
      sessionId: "ses-1",
      file: makeFile("second.pdf", 5, "application/pdf"),
    });
    await removeAttachment("ses-1", first.id);
    const remaining = await listAttachments("ses-1");
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.id).toBe(second.id);
  });

  it("uploadAttachment aborts with error status when signal fires", async () => {
    const controller = new AbortController();
    const file = makeFile("slow.pdf", 100, "application/pdf");
    const promise = uploadAttachment({
      sessionId: "ses-1",
      file,
      signal: controller.signal,
    });
    setTimeout(() => controller.abort(), 250);
    const result = (await promise) as AttachmentMetadata;
    expect(result.status).toBe("error");
    expect(result.error).toContain("cancel");
  });
});
