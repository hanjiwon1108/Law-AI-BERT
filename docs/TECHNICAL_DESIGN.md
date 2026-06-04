# 기술 설계

## 1. 전체 구조

현재 서비스는 BERT 학습/추론 파이프라인과 웹 UI로 구성된다.

```text
data/contract_clauses_labeled.csv
  -> scripts/train_bert.py
      -> models/contract-risk-bert
  -> scripts/serve_bert.py
      -> POST /analyze
  -> index.html + app.js
      -> BERT API result rendering
```

## 2. 현재 분석 방식

현재 버전은 `klue/bert-base`를 계약 조항 이진 분류 데이터셋으로 파인튜닝한다. 모델은 각 조항을 `SAFE` 또는 `RISK`로 분류한다. 웹 UI는 로컬 API가 실행 중이면 BERT 결과를 우선 사용한다.

규칙 기반 로직은 모델 서버가 꺼져 있을 때 데모 화면이 동작하도록 남겨 둔 임시 폴백이며, 최종 판단의 기준은 BERT 모델 출력이다.

### MVP 위험도 산식

현재 점수는 조항별 위험 가중치와 전체 위험 조항 비율을 함께 반영한다.

```text
전체 위험도 = min(100, 조항별 위험 점수 평균 + 위험 조항 비율 * 45)
```

등급 기준은 다음과 같다.

| 점수 | 등급 |
| --- | --- |
| 60 이상 | 높은 위험 |
| 30 이상 60 미만 | 주의 필요 |
| 1 이상 30 미만 | 낮은 위험 |
| 0 | 위험 낮음 |

### BERT 학습 명령

```bash
python3 scripts/train_bert.py \
  --data data/contract_clauses_labeled.csv \
  --model-name klue/bert-base \
  --output-dir models/contract-risk-bert \
  --epochs 3
```

### 추론 API

```bash
python3 scripts/serve_bert.py --model-dir models/contract-risk-bert --port 8000
```

요청:

```json
{
  "text": "계약 해지 시 위약금 500만 원을 지급하여야 한다.",
  "contractType": "freelance"
}
```

응답은 웹 UI의 리포트 구조와 동일하다.

### 장점

- BERT가 키워드뿐 아니라 문맥을 반영해 위험 여부를 분류한다.
- 학습 데이터셋을 확장하면 같은 코드로 성능을 개선할 수 있다.
- 모델, 토크나이저, 학습 메타데이터가 `models/contract-risk-bert`에 저장된다.
- 웹 UI와 API 응답 구조가 분리되어 배포 구성이 명확하다.

### 한계

- 현재 포함된 데이터셋은 프로젝트용 시드 데이터이므로 실제 서비스에는 더 많은 공개 계약서와 전문가 라벨링 데이터가 필요하다.
- 이진 분류 모델은 위험 유형을 직접 예측하지 않는다. 현재 위험 유형과 설명은 BERT가 `RISK`로 분류한 뒤 보조 규칙으로 매핑한다.
- 실제 법률적 위험 판단을 대체할 수 없다.

## 3. BERT 기반 구조

구조는 다음과 같다.

```text
Frontend
  -> Contract text
  -> Backend API
      -> Text preprocessing
      -> Clause segmentation
      -> Fine-tuned BERT classifier
      -> Risk explanation generator
  -> Report JSON
  -> Frontend rendering
```

## 4. 모델 설계

### 모델

- Base model: `klue/bert-base`
- Task: Binary classification
- Labels:
  - `0`: 일반 조항
  - `1`: 위험 조항

### 입력

```python
inputs = tokenizer(
    text,
    padding="max_length",
    truncation=True,
    max_length=256,
    return_tensors="pt",
)
```

### 모델

```python
from transformers import BertForSequenceClassification

model = BertForSequenceClassification.from_pretrained(
    "klue/bert-base",
    num_labels=2,
)
```

### 학습

```python
outputs = model(
    input_ids=input_ids,
    attention_mask=attention_mask,
    labels=labels,
)

loss = outputs.loss
loss.backward()
optimizer.step()
```

### 예측

```python
prediction = torch.argmax(outputs.logits, dim=1)
```

## 5. 데이터셋 설계

### 수집 대상

- 근로계약서
- 임대차계약서
- 프리랜서 계약서
- 서비스 이용약관

### 라벨

| label | 의미 |
| --- | --- |
| 0 | 일반 조항 |
| 1 | 위험 조항 |

### 전처리

1. 특수문자 및 불필요한 공백 제거
2. 중복 데이터 제거
3. 결측 데이터 제거
4. 계약서 조항 단위 분리
5. BERT 입력 형식 변환
6. 학습 데이터와 테스트 데이터 분할

## 6. API 응답 형식 초안

```json
{
  "score": 74,
  "riskLevel": "high",
  "clauses": [
    {
      "id": "clause-1",
      "text": "계약 해지 시 위약금 500만 원을 지급하여야 한다.",
      "risk": true,
      "category": "과도한 위약금",
      "confidence": 0.91,
      "evidence": ["계약 해지", "위약금"],
      "explanation": "해지 시 고정 금액의 위약금을 부담하도록 하므로 실제 손해보다 과도할 가능성이 있습니다.",
      "questions": [
        "위약금 산정 기준이 명확한가?",
        "실제 손해액과 비교해 과도하지 않은가?"
      ]
    }
  ]
}
```

프론트엔드는 이 응답 형태를 기준으로 렌더링하므로, 현재 규칙 기반 분석기를 API 호출로 교체할 수 있다.

## 7. 개인정보 보호

- MVP는 서버 전송 없이 브라우저 안에서만 분석한다.
- 실제 서비스에서는 주민등록번호, 주소, 전화번호, 계좌번호 등 개인정보 비식별화가 필요하다.
- 계약서 원문 저장은 기본 비활성화해야 한다.
- 학습 데이터로 사용할 경우 사용자 동의를 별도로 받아야 한다.
