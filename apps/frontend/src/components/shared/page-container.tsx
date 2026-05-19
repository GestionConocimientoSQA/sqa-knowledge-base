import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Wrapper estándar para páginas de la app: max-width, padding y respiración.
 * SRP: solo se encarga de la composición espacial; nada de lógica.
 */
export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-[1440px] px-6 py-8 sm:px-8 lg:px-10",
        className,
      )}
    >
      {children}
    </div>
  );
}
