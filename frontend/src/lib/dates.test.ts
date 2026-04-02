import { describe, expect, it } from "vitest";

import { parseApiDate } from "./dates";

describe("parseApiDate", () => {
  it("treats backend timestamps without a timezone suffix as UTC", () => {
    expect(parseApiDate("2026-04-01T17:21:10.549135").toISOString()).toBe("2026-04-01T17:21:10.549Z");
  });

  it("preserves timestamps that already include timezone information", () => {
    expect(parseApiDate("2026-04-01T17:21:10.549135Z").toISOString()).toBe("2026-04-01T17:21:10.549Z");
  });
});
