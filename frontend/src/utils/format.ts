export function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}
