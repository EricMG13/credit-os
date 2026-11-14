import "@testing-library/jest-dom/vitest";

// jsdom has no layout. A chart's responsive container reads its size from ResizeObserver, so the
// tests give every observed element a fixed size, as a laid-out browser would.
class FixedResizeObserver implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}
  observe(target: Element): void {
    const rect = { width: 600, height: 240, x: 0, y: 0, top: 0, left: 0, right: 600, bottom: 240 };
    const size = [{ inlineSize: 600, blockSize: 240 }];
    this.callback(
      [
        {
          target,
          contentRect: { ...rect, toJSON: () => rect },
          borderBoxSize: size,
          contentBoxSize: size,
          devicePixelContentBoxSize: size,
        },
      ],
      this,
    );
  }
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver = FixedResizeObserver;
