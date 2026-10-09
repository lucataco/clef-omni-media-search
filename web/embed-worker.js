// Sentence embeddings for paraphrase matching ("spectacles" -> glasses), off the main thread so
// downloading and compiling the model never blocks typing or the tile animations.
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3";

env.allowLocalModels = false;
const ready = pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", { dtype: "q8" });

self.onmessage = async ({ data: { id, texts } }) => {
  try {
    const fe = await ready;
    const out = await fe(texts, { pooling: "mean", normalize: true });
    const d = out.dims[1];
    const vecs = texts.map((_, k) => out.data.slice(k * d, (k + 1) * d));
    self.postMessage({ id, vecs }, vecs.map((v) => v.buffer));
  } catch (err) {
    self.postMessage({ id, error: String(err) });
  }
};
