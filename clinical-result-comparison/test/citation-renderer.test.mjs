import assert from "node:assert/strict";
import test from "node:test";
import { parseCitationJson, renderCitationMarkers, renderCitationReport } from "../runtime/citation-renderer.mjs";

test("renders safe superscript links from a separate citation JSON object", () => {
  const rendered = renderCitationReport("Claim{{ref_1}}", {
    ref_1: { title: "Source", link: "https://example.com/source", paper_release_time_str: "2025-01-01" }
  });
  assert.match(rendered, /href="https:\/\/example\.com\/source"/);
  assert.match(rendered, />1<\/a><\/sup>/);
});

test("parses strict citation JSON including release time", () => {
  assert.deepEqual(parseCitationJson('{"ref_1":{"title":"Source","link":"https://example.com/source","paper_release_time_str":"2025-01-01"}}'), {
    ref_1: { title: "Source", link: "https://example.com/source", paper_release_time_str: "2025-01-01" }
  });
});

test("supports markers from separate trials in one shared report", () => {
  const citations = {
    ref_1: { title: "Trial A", link: "https://example.com/a", paper_release_time_str: "" },
    ref_2: { title: "Trial B", link: "https://example.com/b", paper_release_time_str: "" }
  };
  const rendered = renderCitationMarkers("Trial A 48%{{ref_1}}; Trial B 55%{{ref_2}}", citations);
  assert.match(rendered, /href="https:\/\/example\.com\/a"[^>]*>1<\/a>/);
  assert.match(rendered, /href="https:\/\/example\.com\/b"[^>]*>2<\/a>/);
});

test("leaves empty or unsafe links as inert markers", () => {
  assert.equal(renderCitationMarkers("value{{ref_1}}", { ref_1: { title: "Missing", link: "", paper_release_time_str: "" } }), "value{{ref_1}}");
  assert.equal(renderCitationMarkers("value{{ref_1}}", { ref_1: { title: "Unsafe", link: "javascript:alert(1)", paper_release_time_str: "" } }), "value{{ref_1}}");
});

test("escapes supplied metadata before HTML interpolation", () => {
  const rendered = renderCitationMarkers("value{{ref_1}}", {
    ref_1: { title: "A & \"B\" <C>", link: "https://example.com/?a=1&b=2", paper_release_time_str: "2025-01-01" }
  });
  assert.match(rendered, /href="https:\/\/example\.com\/\?a=1&amp;b=2"/);
  assert.match(rendered, /title="A &amp; &quot;B&quot; &lt;C&gt;"/);
});

test("rejects marker and JSON key mismatches", () => {
  assert.throws(() => renderCitationReport("Claim{{ref_1}}", {
    ref_2: { title: "x", link: "https://example.com", paper_release_time_str: "" }
  }), /citation_marker_key_mismatch/);
});
