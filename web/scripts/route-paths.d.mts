export function pathsIn(source: string): string[];
export function declaredPaths(groupDir: string): string[];
export function fillParams(
  p: string,
  s: Record<string, string>,
): { hash: string; missing: string[] };
export function declaresHome(source: string): boolean;
export function groupDeclaresHome(groupDir: string): boolean;
