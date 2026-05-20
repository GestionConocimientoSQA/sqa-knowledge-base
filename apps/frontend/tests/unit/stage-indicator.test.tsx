import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StageIndicator } from "@/components/chat/stage-indicator";

describe("StageIndicator", () => {
  describe("modo captura (stepper 0-5)", () => {
    it("currentStage=null: ningún paso lleva aria-current", () => {
      render(<StageIndicator mode="captura" currentStage={null} />);
      const list = screen.getByRole("list", { name: /etapas de la captura/i });
      const steps = within(list).getAllByRole("listitem");
      expect(steps).toHaveLength(6);
      for (const step of steps) {
        expect(step.getAttribute("aria-current")).toBeNull();
      }
    });

    it("marca la etapa activa con aria-current='step'", () => {
      render(<StageIndicator mode="captura" currentStage={2} />);
      const list = screen.getByRole("list", { name: /etapas de la captura/i });
      const steps = within(list).getAllByRole("listitem");
      const current = steps.filter(
        (s) => s.getAttribute("aria-current") === "step",
      );
      expect(current).toHaveLength(1);
      expect(within(current[0]!).getByText("Captura libre")).toBeInTheDocument();
    });

    it("etapas previas a la actual aparecen completadas (con check, no número)", () => {
      render(<StageIndicator mode="captura" currentStage={3} />);
      // Las etapas 0,1,2 ya no muestran su número; aparecen 3,4,5 visibles.
      expect(screen.queryByText("0")).toBeNull();
      expect(screen.queryByText("1")).toBeNull();
      expect(screen.queryByText("2")).toBeNull();
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("renderiza los 6 labels de etapa", () => {
      render(<StageIndicator mode="captura" currentStage={0} />);
      for (const label of [
        "Bienvenida",
        "Identificación",
        "Captura libre",
        "Profundización",
        "Validación",
        "Generación",
      ]) {
        expect(screen.getByText(label)).toBeInTheDocument();
      }
    });
  });

  describe("modo consulta (pill C)", () => {
    it("muestra letra C y label de consulta", () => {
      render(<StageIndicator mode="consulta" currentStage="C" />);
      expect(screen.getByText("C")).toBeInTheDocument();
      expect(
        screen.getByText(/consultando base de conocimiento/i),
      ).toBeInTheDocument();
    });

    it("no renderiza el stepper de captura", () => {
      render(<StageIndicator mode="consulta" currentStage="C" />);
      expect(
        screen.queryByRole("list", { name: /etapas de la captura/i }),
      ).toBeNull();
    });
  });

  describe("modo ingesta (pill I)", () => {
    it("muestra letra I y label de ingesta", () => {
      render(<StageIndicator mode="ingesta" currentStage="I" />);
      expect(screen.getByText("I")).toBeInTheDocument();
      expect(screen.getByText(/clasificando documento/i)).toBeInTheDocument();
    });
  });
});
