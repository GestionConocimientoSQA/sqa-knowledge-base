import { DOCS, FOLDERS } from "@/lib/mocks/data";
import type { Category, DocumentItem } from "@/types/domain";

const STUB_DELAY_MS = 250;

function delay<T>(value: T, ms = STUB_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function listDocuments(): Promise<DocumentItem[]> {
  return delay(DOCS);
}

export async function getDocument(id: string): Promise<DocumentItem | null> {
  return delay(DOCS.find((d) => d.id === id) ?? null);
}

export async function listCategories(): Promise<Category[]> {
  return delay(FOLDERS);
}
