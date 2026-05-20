import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AttachmentChip } from "@/components/chat/attachment-chip";
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

describe("AttachmentChip", () => {
  it("uploaded: muestra filename y tamaño formateado", () => {
    render(<AttachmentChip attachment={makeAttachment()} />);
    expect(screen.getByText("plan.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });

  it("uploading: muestra porcentaje en lugar de tamaño", () => {
    render(
      <AttachmentChip
        attachment={makeAttachment({ status: "uploading", progress: 42 })}
      />,
    );
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.queryByText("2.0 KB")).not.toBeInTheDocument();
  });

  it("error: aplica clase destructive y muestra el mensaje de error", () => {
    const { container } = render(
      <AttachmentChip
        attachment={makeAttachment({
          status: "error",
          error: "Archivo muy grande",
        })}
      />,
    );
    expect(screen.getByText("Archivo muy grande")).toBeInTheDocument();
    expect(container.querySelector(".text-destructive")).not.toBeNull();
  });

  it("error sin mensaje: cae a 'Error' por defecto", () => {
    render(
      <AttachmentChip attachment={makeAttachment({ status: "error" })} />,
    );
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("botón X tiene type='button' y dispara onRemove sin submitear", () => {
    const onRemove = vi.fn();
    const submit = vi.fn((e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
    });
    render(
      <form onSubmit={submit}>
        <AttachmentChip attachment={makeAttachment()} onRemove={onRemove} />
      </form>,
    );
    const button = screen.getByLabelText("Quitar plan.pdf") as HTMLButtonElement;
    expect(button.type).toBe("button");
    fireEvent.click(button);
    expect(onRemove).toHaveBeenCalledWith("att-1");
    expect(submit).not.toHaveBeenCalled();
  });

  it("botón X queda deshabilitado mientras uploading (no se puede quitar a mitad)", () => {
    const onRemove = vi.fn();
    render(
      <AttachmentChip
        attachment={makeAttachment({ status: "uploading", progress: 30 })}
        onRemove={onRemove}
      />,
    );
    const button = screen.getByLabelText("Quitar plan.pdf") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("sin onRemove: no se renderiza el botón X", () => {
    render(<AttachmentChip attachment={makeAttachment()} />);
    expect(screen.queryByLabelText("Quitar plan.pdf")).toBeNull();
  });
});
