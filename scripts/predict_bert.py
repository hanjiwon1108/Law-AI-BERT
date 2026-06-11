import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from contract_nlp import infer_category, risk_level, split_into_clauses


def choose_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class BertRiskPredictor:
    def __init__(self, model_dir: str, max_length: int = 256):
        start = time.perf_counter()
        self.device = choose_device()
        import sys
        print(f"[model] device={self.device}", flush=True, file=sys.stderr)
        print(f"[model] loading tokenizer from {model_dir}", flush=True, file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        print(f"[model] loading model from {model_dir}", flush=True, file=sys.stderr)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_dir, attn_implementation="eager"
        )
        print("[model] moving model to device", flush=True, file=sys.stderr)
        self.model.to(self.device)
        self.model.eval()
        self.max_length = max_length
        elapsed = time.perf_counter() - start
        print(f"[model] ready in {elapsed:.2f}s", flush=True, file=sys.stderr)

    def _extract_attention_spans(self, text: str, encoded: dict) -> list:
        """Return character-level [start, end] spans using gradient-based attribution.

        Computes d(risk_logit) / d(embedding) · embedding (input × gradient),
        then takes the L2 norm per token as importance score.
        This reflects which tokens actually drove the RISK classification decision.
        """
        encoded_with_offsets = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
            return_offsets_mapping=True,
        )
        offset_mapping = encoded_with_offsets.pop("offset_mapping")[0]
        input_ids = encoded_with_offsets["input_ids"][0].cpu()

        encoded_device = {k: v.to(self.device) for k, v in encoded_with_offsets.items()}

        # Get the embedding layer and compute gradients through it
        embedding_layer = self.model.bert.embeddings.word_embeddings
        input_embeds = embedding_layer(encoded_device["input_ids"])  # (1, seq, hidden)
        input_embeds = input_embeds.detach().requires_grad_(True)

        outputs = self.model(
            inputs_embeds=input_embeds,
            attention_mask=encoded_device.get("attention_mask"),
            token_type_ids=encoded_device.get("token_type_ids"),
        )
        risk_logit = outputs.logits[0, 1]  # logit for RISK class
        risk_logit.backward()

        # input × gradient, L2 norm per token → importance score
        grads = input_embeds.grad[0]  # (seq, hidden)
        scores = (input_embeds.detach()[0] * grads).norm(dim=-1).cpu().float()  # (seq,)

        special_ids = {
            self.tokenizer.cls_token_id,
            self.tokenizer.sep_token_id,
            self.tokenizer.pad_token_id,
        }

        token_spans = []
        for i, (tid, (char_start, char_end)) in enumerate(zip(input_ids.tolist(), offset_mapping.tolist())):
            if tid in special_ids or char_start == char_end:
                continue
            token_spans.append((int(char_start), int(char_end), float(scores[i])))

        if not token_spans:
            return []

        score_vals = torch.tensor([s for _, _, s in token_spans])
        # Keep only top 15% of tokens — avoids marking everything as important
        threshold = float(torch.quantile(score_vals, 0.85))

        spans = []
        current_start = None
        current_end = None

        for char_start, char_end, score in token_spans:
            if score >= threshold:
                if current_start is None:
                    current_start = char_start
                    current_end = char_end
                elif char_start <= current_end + 2:
                    current_end = char_end
                else:
                    spans.append([current_start, current_end])
                    current_start = char_start
                    current_end = char_end
            else:
                if current_start is not None:
                    spans.append([current_start, current_end])
                    current_start = None
                    current_end = None

        if current_start is not None:
            spans.append([current_start, current_end])

        return spans

    def predict_clause(self, text: str, index: int):
        encoded = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = self.model(**encoded).logits
            probs = torch.softmax(logits, dim=1).squeeze(0).detach().cpu()

        risk_probability = float(probs[1])
        is_risk = risk_probability >= 0.5
        info = infer_category(text) if is_risk else {
            "category": "일반 조항",
            "severity": "low",
            "evidence": [],
            "explanation": "BERT 모델이 일반 조항으로 분류했습니다.",
            "questions": ["계약 기간, 대금, 해지 조건 등 핵심 조건이 명확한지 확인하세요."],
        }

        attention_spans = self._extract_attention_spans(text, encoded) if is_risk else []

        return {
            "id": f"clause-{index}",
            "index": index,
            "text": text,
            "risk": is_risk,
            "category": info["category"],
            "severity": info["severity"],
            "score": round(risk_probability * 100),
            "confidence": round(risk_probability if is_risk else float(probs[0]), 4),
            "evidence": info["evidence"],
            "attentionSpans": attention_spans,
            "explanation": info["explanation"],
            "questions": info["questions"],
            "modelLabel": "RISK" if is_risk else "SAFE",
        }

    def analyze(self, text: str, contract_type: str = "general"):
        clauses = split_into_clauses(text)
        analyzed = [self.predict_clause(clause, index + 1) for index, clause in enumerate(clauses)]
        risky = [clause for clause in analyzed if clause["risk"]]
        category_counts = {}
        for clause in risky:
            category_counts[clause["category"]] = category_counts.get(clause["category"], 0) + 1

        raw_score = sum(clause["score"] for clause in risky)
        risk_ratio = len(risky) / len(clauses) if clauses else 0
        score = min(100, round(raw_score / max(1, len(clauses)) + risk_ratio * 45))
        top_category = sorted(category_counts.items(), key=lambda item: item[1], reverse=True)[0][0] if category_counts else "-"

        return {
            "source": "bert",
            "contractType": contract_type,
            "score": score,
            "level": risk_level(score),
            "clauses": analyzed,
            "riskyCount": len(risky),
            "categoryCounts": category_counts,
            "topCategory": top_category,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict contract risk clauses with a fine-tuned BERT model.")
    parser.add_argument("--model-dir", default="models/contract-risk-bert")
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--contract-type", default="general")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        raise SystemExit("--text or --file is required")

    predictor = BertRiskPredictor(args.model_dir)
    print(json.dumps(predictor.analyze(text, args.contract_type), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
