import type { Annotation } from '../data/case';

export type AnchorResolution =
  | { annotation: Annotation; status: 'ok'; start: number; end: number }
  | { annotation: Annotation; status: 'ambiguous' | 'unresolved'; start: null; end: null };

export function resolveAnnotations(text: string, annotations: Annotation[]): AnchorResolution[] {
  return annotations.map((annotation) => {
    const matches: Array<{ start: number; end: number }> = [];
    let from = 0;
    for (;;) {
      const idx = text.indexOf(annotation.exact, from);
      if (idx === -1) break;
      const before = text.slice(idx - annotation.prefix.length, idx);
      const after = text.slice(idx + annotation.exact.length, idx + annotation.exact.length + annotation.suffix.length);
      if (before === annotation.prefix && after === annotation.suffix) {
        matches.push({ start: idx, end: idx + annotation.exact.length });
      }
      from = idx + 1;
    }
    if (matches.length === 1) {
      return { annotation, status: 'ok', start: matches[0].start, end: matches[0].end };
    }
    return { annotation, status: matches.length > 1 ? 'ambiguous' : 'unresolved', start: null, end: null };
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export type AnnotatedSegment = { html: string; kind: 'text' | 'mark'; label: string | null };

export function annotateHtml(text: string, resolutions: AnchorResolution[]): AnnotatedSegment[] {
  const ok = resolutions
    .filter((r): r is Extract<AnchorResolution, { status: 'ok' }> => r.status === 'ok')
    .sort((a, b) => a.start - b.start);
  const segments: AnnotatedSegment[] = [];
  let cursor = 0;
  for (const r of ok) {
    if (r.start < cursor) continue;
    if (r.start > cursor) {
      segments.push({ html: escapeHtml(text.slice(cursor, r.start)), kind: 'text', label: null });
    }
    segments.push({
      html: escapeHtml(text.slice(r.start, r.end)),
      kind: 'mark',
      label: r.annotation.label,
    });
    cursor = r.end;
  }
  if (cursor < text.length) {
    segments.push({ html: escapeHtml(text.slice(cursor)), kind: 'text', label: null });
  }
  return segments;
}
