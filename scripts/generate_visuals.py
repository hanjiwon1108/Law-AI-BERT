import json
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_bert import ClauseDataset, choose_device, read_rows, split_rows


def load_metadata(model_dir: Path) -> dict:
    metadata_path = model_dir / "training_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError("training_metadata.json not found in model directory.")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def plot_loss(history: list, out_path: Path) -> None:
    epochs = [item["epoch"] for item in history]
    train_loss = [item["train_loss"] for item in history]
    val_loss = [item["loss"] for item in history]

    plt.figure(figsize=(6, 4), dpi=160)
    plt.plot(epochs, train_loss, marker="o", label="Train loss")
    plt.plot(epochs, val_loss, marker="o", label="Val loss")
    plt.title("Training vs Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.xticks(epochs)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def plot_accuracy(history: list, out_path: Path) -> None:
    epochs = [item["epoch"] for item in history]
    accuracy = [item["accuracy"] for item in history]

    plt.figure(figsize=(6, 4), dpi=160)
    plt.plot(epochs, accuracy, marker="o", color="#145c72")
    plt.title("Validation Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.ylim(0, 1)
    plt.xticks(epochs)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def build_confusion_matrix(model_dir: Path, data_path: Path, config: dict) -> list:
    rows = read_rows(data_path)
    train_rows, test_rows = split_rows(rows, config["test_ratio"], config["seed"])

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    device = choose_device()
    model.to(device)
    model.eval()

    loader = DataLoader(
        ClauseDataset(test_rows, tokenizer, config["max_length"]),
        batch_size=config["batch_size"],
    )

    tn = fp = fn = tp = 0
    with torch.no_grad():
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            preds = torch.argmax(outputs.logits, dim=1)
            labels = batch["labels"]

            tn += int(((preds == 0) & (labels == 0)).sum().cpu())
            fp += int(((preds == 1) & (labels == 0)).sum().cpu())
            fn += int(((preds == 0) & (labels == 1)).sum().cpu())
            tp += int(((preds == 1) & (labels == 1)).sum().cpu())

    return [[tn, fp], [fn, tp]]


def plot_confusion_matrix(matrix: list, out_path: Path) -> None:
    labels = ["SAFE", "RISK"]
    plt.figure(figsize=(5, 4), dpi=160)
    plt.imshow(matrix, cmap="Blues")
    plt.title("Confusion Matrix (Test)")
    plt.xticks([0, 1], labels)
    plt.yticks([0, 1], labels)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")

    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(matrix[i][j]), ha="center", va="center", color="#0f4353")

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    model_dir = root / "models" / "contract-risk-bert"
    data_path = root / "data" / "contract_clauses_labeled.csv"
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_metadata(model_dir)
    history = metadata["history"]
    config = metadata["config"]

    plot_loss(history, out_dir / "loss_curve.png")
    plot_accuracy(history, out_dir / "accuracy_curve.png")

    matrix = build_confusion_matrix(model_dir, data_path, config)
    plot_confusion_matrix(matrix, out_dir / "confusion_matrix.png")

    print("Saved graphs to:")
    print(out_dir / "loss_curve.png")
    print(out_dir / "accuracy_curve.png")
    print(out_dir / "confusion_matrix.png")


if __name__ == "__main__":
    main()
