import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MessageBubble } from "@/components/chat/message-bubble";
import type { AgentMessage } from "@/types/agent";

function renderBubble(ui: React.ReactElement) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

function makeAgentMessage(partial: Partial<AgentMessage> = {}): AgentMessage {
  return {
    id: "m1",
    role: "agent",
    content: "",
    stage: null,
    status: "complete",
    startedAt: "2026-05-19T12:00:00.000Z",
    endedAt: "2026-05-19T12:00:01.000Z",
    durationMs: 1000,
    classification: null,
    citations: [],
    scoring: null,
    artifacts: [],
    tokenUsage: null,
    error: null,
    ...partial,
  };
}

describe("MessageBubble", () => {
  // MessageContent (que renderiza Markdown) es dynamic-imported por
  // next/dynamic para code-splitting. En jsdom hay un tick async hasta
  // que el componente carga — usamos `findBy*` (async) para esperar.

  it("renderiza Markdown básico (párrafo, bold, lista)", async () => {
    const message = makeAgentMessage({
      content: "**Hola** Aria\n\n- uno\n- dos",
    });
    renderBubble(<MessageBubble message={message} />);
    expect(await screen.findByText("Hola")).toBeInTheDocument();
    expect(screen.getByText("uno")).toBeInTheDocument();
    expect(screen.getByText("dos")).toBeInTheDocument();
  });

  it("links externos abren en nueva pestaña con rel='noopener noreferrer nofollow'", async () => {
    const message = makeAgentMessage({
      content: "Ver [docs](https://example.com/policy)",
    });
    renderBubble(<MessageBubble message={message} />);
    const link = await screen.findByRole("link", { name: "docs" });
    expect(link.getAttribute("href")).toBe("https://example.com/policy");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer nofollow");
  });

  it("links relativos no abren en nueva pestaña ni agregan rel", async () => {
    const message = makeAgentMessage({
      content: "Ver [interna](/explorer/doc-1)",
    });
    renderBubble(<MessageBubble message={message} />);
    const link = await screen.findByRole("link", { name: "interna" });
    expect(link.getAttribute("href")).toBe("/explorer/doc-1");
    expect(link.getAttribute("target")).toBeNull();
    expect(link.getAttribute("rel")).toBeNull();
  });

  it("footer de tokenUsage NO se muestra por defecto (showTokenUsage=false)", () => {
    const message = makeAgentMessage({
      content: "respuesta",
      tokenUsage: {
        inputTokens: 1240,
        outputTokens: 380,
        costUsd: 0.0124,
        model: "claude-sonnet-4-6",
      },
    });
    renderBubble(<MessageBubble message={message} />);
    expect(screen.queryByText(/USD 0\.0124/)).toBeNull();
    expect(screen.queryByText(/claude-sonnet-4-6/)).toBeNull();
  });

  it("footer de tokenUsage se muestra cuando showTokenUsage=true (admin)", () => {
    const message = makeAgentMessage({
      content: "respuesta",
      tokenUsage: {
        inputTokens: 1240,
        outputTokens: 380,
        costUsd: 0.0124,
        model: "claude-sonnet-4-6",
      },
    });
    renderBubble(<MessageBubble message={message} showTokenUsage />);
    // Tolerar separador de miles según locale del runner (es: "1.240", en: "1,240").
    expect(
      screen.getByText(
        /1[.,]240\s+in · 380 out · USD 0\.0124 · claude-sonnet-4-6/,
      ),
    ).toBeInTheDocument();
  });

  it("mensaje del usuario: muestra avatar con iniciales y aria-label correcto", () => {
    const message = makeAgentMessage({
      role: "user",
      content: "hola",
      tokenUsage: {
        inputTokens: 1,
        outputTokens: 1,
        costUsd: 0.0001,
        model: "x",
      },
    });
    renderBubble(<MessageBubble message={message} userInitials="AA" showTokenUsage />);
    expect(screen.getByLabelText("Mensaje del usuario")).toBeInTheDocument();
    expect(screen.getByText("AA")).toBeInTheDocument();
    // tokenUsage no se muestra en mensajes del usuario aunque showTokenUsage=true
    expect(screen.queryByText(/USD 0\.0001/)).toBeNull();
  });

  it("renderiza ClassificationCard cuando classification está presente", () => {
    const message = makeAgentMessage({
      content: "ok",
      classification: {
        category: "PROC",
        documentType: "POL",
        confidence: 0.92,
        rationale: "Coincide con el formato de POL",
      },
    });
    renderBubble(<MessageBubble message={message} />);
    expect(screen.getByText(/PROC/)).toBeInTheDocument();
  });

  it("renderiza chips de citación cuando hay citations", () => {
    const message = makeAgentMessage({
      content: "ok",
      citations: [
        {
          documentId: "doc-1",
          filename: "POL-onboarding.docx",
          section: "§3.1",
          snippet: "El proceso comienza...",
        },
        {
          documentId: "doc-2",
          filename: "PROC-seguridad.docx",
          section: "§4",
          snippet: "Para autenticar...",
        },
      ],
    });
    renderBubble(<MessageBubble message={message} />);
    expect(screen.getByLabelText("2 citaciones")).toBeInTheDocument();
  });

  it("renderiza panel de errores cuando status=error", () => {
    const message = makeAgentMessage({
      status: "error",
      content: "",
      error: {
        type: "transport",
        message: "Conexión perdida",
        retryable: true,
      },
    });
    renderBubble(<MessageBubble message={message} />);
    expect(screen.getByText("Conexión perdida")).toBeInTheDocument();
  });

  it("renderiza DocumentArtifactCard cuando hay artifacts", () => {
    const message = makeAgentMessage({
      content: "ok",
      artifacts: [
        {
          documentId: "doc-1",
          filename: "POL-nueva.docx",
          downloadUrl: "/blob/doc-1",
          blobPath: "containers/docs/doc-1.docx",
        },
      ],
    });
    renderBubble(<MessageBubble message={message} />);
    expect(screen.getByLabelText("Documentos generados")).toBeInTheDocument();
    expect(screen.getByText(/POL-nueva\.docx/)).toBeInTheDocument();
  });
});
