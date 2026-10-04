export interface DetailsNode {
  tagName: string;
  open: boolean;
  parentElement: DetailsNode | null;
}

export function openDetailsChain(target: DetailsNode | null): void {
  if (!target) return;
  if (target.tagName === 'DETAILS') target.open = true;
  let p = target.parentElement;
  while (p) {
    if (p.tagName === 'DETAILS') p.open = true;
    p = p.parentElement;
  }
}
