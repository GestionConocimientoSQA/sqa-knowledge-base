import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Composer } from "@/components/chat/composer";
import type { AttachmentMetadata } from "@/types/agent";

function makeAttachment(
  partial: Partial<AttachmentMetadata> = {},
): AttachmentMetadata {
  return {
    id: "att-1",
    sessionId: "ses-1",
    filename: "plan.pdf",
    size: 2048,
    mimeType: "application/pdf",
    status: "uploaded",
    progress: 100,
    uploadedAt: "2026-05-19T12:00:00.000Z",
    ...partial,
  };
}

describe("Composer", () => {
  it("clicking the remove button on an attachment chip does not submit the form", () => {
    // Regresión: el botón X del chip antes era type="submit" implícito, lo
    // que disparaba un envío con mensaje en blanco al quitar el adjunto.
    const onSend = vi.fn();
    const onAttachmentRemove = vi.fn();
    render(
      <Composer
        onSend={onSend}
        attachments={[makeAttachment()]}
        onAttachmentAdd={() => {}}
        onAttachmentRemove={onAttachmentRemove}
      />,
    );
    const removeButton = screen.getByLabelText("Quitar plan.pdf");
    fireEvent.click(removeButton);
    expect(onAttachmentRemove).toHaveBeenCalledWith("att-1");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("submit button stays disabled when only empty whitespace is typed", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByLabelText("Mensaje para Aria");
    fireEvent.change(textarea, { target: { value: "   " } });
    const submit = screen.getByLabelText("Enviar mensaje") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("submit fires when there is text content", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByLabelText("Mensaje para Aria");
    fireEvent.change(textarea, { target: { value: "Hola Aria" } });
    fireEvent.click(screen.getByLabelText("Enviar mensaje"));
    expect(onSend).toHaveBeenCalledWith("Hola Aria");
  });
});
