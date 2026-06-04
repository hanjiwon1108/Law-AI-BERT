import argparse
import csv
import json
import random
from pathlib import Path
from typing import Dict, List

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup


class ClauseDataset(Dataset):
    def __init__(self, rows: List[Dict[str, str]], tokenizer, max_length: int):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        row = self.rows[index]
        encoded = self.tokenizer(
            row["text"],
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": torch.tensor(int(row["label"]), dtype=torch.long),
        }


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"text", "label", "category"}
    if not rows or not required.issubset(rows[0].keys()):
        raise ValueError(f"Dataset must contain columns: {sorted(required)}")
    return [row for row in rows if row["text"].strip() and row["label"] in {"0", "1"}]


def split_rows(rows: List[Dict[str, str]], test_ratio: float, seed: int):
    rng = random.Random(seed)
    by_label = {"0": [], "1": []}
    for row in rows:
        by_label[row["label"]].append(row)

    train_rows = []
    test_rows = []
    for label_rows in by_label.values():
        rng.shuffle(label_rows)
        test_size = max(1, int(len(label_rows) * test_ratio))
        test_rows.extend(label_rows[:test_size])
        train_rows.extend(label_rows[test_size:])

    rng.shuffle(train_rows)
    rng.shuffle(test_rows)
    return train_rows, test_rows


def choose_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def evaluate(model, loader, device: torch.device) -> Dict[str, float]:
    model.eval()
    correct = 0
    total = 0
    tp = fp = fn = 0
    total_loss = 0.0

    with torch.no_grad():
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            total_loss += float(outputs.loss.detach().cpu())
            preds = torch.argmax(outputs.logits, dim=1)
            labels = batch["labels"]
            correct += int((preds == labels).sum().detach().cpu())
            total += int(labels.numel())
            tp += int(((preds == 1) & (labels == 1)).sum().detach().cpu())
            fp += int(((preds == 1) & (labels == 0)).sum().detach().cpu())
            fn += int(((preds == 0) & (labels == 1)).sum().detach().cpu())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "loss": total_loss / max(1, len(loader)),
        "accuracy": correct / max(1, total),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune BERT for Korean contract risk clause classification.")
    parser.add_argument("--data", default="data/contract_clauses_labeled.csv")
    parser.add_argument("--model-name", default="klue/bert-base")
    parser.add_argument("--output-dir", default="models/contract-risk-bert")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    data_path = Path(args.data)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(data_path)
    train_rows, test_rows = split_rows(rows, args.test_ratio, args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2,
        id2label={0: "SAFE", 1: "RISK"},
        label2id={"SAFE": 0, "RISK": 1},
    )

    device = choose_device()
    model.to(device)

    train_loader = DataLoader(ClauseDataset(train_rows, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(ClauseDataset(test_rows, tokenizer, args.max_length), batch_size=args.batch_size)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=max(1, total_steps // 10), num_training_steps=total_steps)

    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            outputs = model(**batch)
            outputs.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            train_loss += float(outputs.loss.detach().cpu())

        metrics = evaluate(model, test_loader, device)
        metrics["epoch"] = epoch
        metrics["train_loss"] = train_loss / max(1, len(train_loader))
        history.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False))

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    metadata = {
        "base_model": args.model_name,
        "labels": {"0": "SAFE", "1": "RISK"},
        "train_size": len(train_rows),
        "test_size": len(test_rows),
        "config": vars(args),
        "history": history,
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved model: {output_dir}")


if __name__ == "__main__":
    main()
