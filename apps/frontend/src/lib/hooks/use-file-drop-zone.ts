"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

interface UseFileDropZoneOptions {
  ref: RefObject<HTMLElement | null>;
  enabled?: boolean;
  onFiles: (files: File[]) => void;
}

/**
 * Hook para soportar drag & drop de archivos sobre un nodo arbitrario.
 *
 * El contador interno (`enterCountRef`) evita el flicker clásico cuando el
 * cursor cruza entre hijos del nodo — `dragleave` se dispara antes que el
 * `dragenter` del hijo, así que sin contador la overlay parpadea.
 */
export function useFileDropZone({
  ref,
  enabled = true,
  onFiles,
}: UseFileDropZoneOptions): { isDragging: boolean } {
  const [isDragging, setIsDragging] = useState(false);
  const enterCountRef = useRef(0);

  const onFilesRef = useRef(onFiles);
  useEffect(() => {
    onFilesRef.current = onFiles;
  }, [onFiles]);

  const handleDragEnter = useCallback((event: DragEvent) => {
    if (!event.dataTransfer?.types.includes("Files")) return;
    event.preventDefault();
    enterCountRef.current += 1;
    setIsDragging(true);
  }, []);

  const handleDragOver = useCallback((event: DragEvent) => {
    if (!event.dataTransfer?.types.includes("Files")) return;
    event.preventDefault();
  }, []);

  const handleDragLeave = useCallback((event: DragEvent) => {
    if (!event.dataTransfer?.types.includes("Files")) return;
    event.preventDefault();
    enterCountRef.current = Math.max(0, enterCountRef.current - 1);
    if (enterCountRef.current === 0) setIsDragging(false);
  }, []);

  const handleDrop = useCallback((event: DragEvent) => {
    if (!event.dataTransfer?.types.includes("Files")) return;
    event.preventDefault();
    enterCountRef.current = 0;
    setIsDragging(false);
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) onFilesRef.current(files);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const node = ref.current;
    if (!node) return;
    node.addEventListener("dragenter", handleDragEnter);
    node.addEventListener("dragover", handleDragOver);
    node.addEventListener("dragleave", handleDragLeave);
    node.addEventListener("drop", handleDrop);
    return () => {
      node.removeEventListener("dragenter", handleDragEnter);
      node.removeEventListener("dragover", handleDragOver);
      node.removeEventListener("dragleave", handleDragLeave);
      node.removeEventListener("drop", handleDrop);
    };
  }, [ref, enabled, handleDragEnter, handleDragOver, handleDragLeave, handleDrop]);

  return { isDragging };
}
