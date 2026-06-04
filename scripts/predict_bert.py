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
        print(f"[model] device={self.device}", flush=True)
        print(f"[model] loading tokenizer from {model_dir}", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        print(f"[model] loading model from {model_dir}", flush=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        print("[model] moving model to device", flush=True)
        self.model.to(self.device)
        self.model.eval()
        self.max_length = max_length
        elapsed = time.perf_counter() - start
        print(f"[model] ready in {elapsed:.2f}s", flush=True)

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
