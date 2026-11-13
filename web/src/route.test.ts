import { act, renderHook } from "@testing-library/react";
import { useHashRoute } from "./route";

function go(hash: string) {
  window.location.hash = hash;
  act(() => {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

afterEach(() => {
  window.location.hash = "";
});

describe("useHashRoute", () => {
  it("is empty when the address has no hash", () => {
    window.location.hash = "";
    const { result } = renderHook(() => useHashRoute());
    expect(result.current).toBe("");
  });

  it("is the part after the hash sign", () => {
    window.location.hash = "#/kit";
    const { result } = renderHook(() => useHashRoute());
    expect(result.current).toBe("/kit");
  });

  it("follows hashchange events", () => {
    window.location.hash = "";
    const { result } = renderHook(() => useHashRoute());
    go("#/kit");
    expect(result.current).toBe("/kit");
    go("");
    expect(result.current).toBe("");
  });

  it("stops listening when unmounted", () => {
    const remove = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useHashRoute());
    unmount();
    expect(remove).toHaveBeenCalledWith("hashchange", expect.any(Function));
    remove.mockRestore();
  });
});
