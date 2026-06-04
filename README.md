# 계약서 위험 조항 탐지 AI

계약 경험이 적은 사용자가 계약서에서 불리하게 작용할 수 있는 조항을 빠르게 확인하도록 돕는 BERT 기반 계약서 위험 조항 탐지 서비스입니다. 라벨링 데이터셋, BERT 파인튜닝 스크립트, 로컬 추론 API, 웹 UI를 포함합니다.

## 실행 방법

### 1. 의존성 설치

```bash
python3 -m pip install -r requirements.txt
```

### 2. BERT 모델 학습

```bash
python3 scripts/train_bert.py \
  --data data/contract_clauses_labeled.csv \
  --model-name klue/bert-base \
  --output-dir models/contract-risk-bert \
  --epochs 3
```

### 3. 학습 모델 예측 테스트

```bash
python3 scripts/predict_bert.py \
  --model-dir models/contract-risk-bert \
  --text "계약 해지 시 위약금 500만 원을 지급하여야 한다."
```

### 4. 로컬 BERT API 실행

```bash
python3 scripts/serve_bert.py --model-dir models/contract-risk-bert --port 8000
```

### 5. 웹 앱 실행

`index.html` 파일을 브라우저에서 열면 됩니다. BERT API가 `http://127.0.0.1:8000`에서 실행 중이면 웹 UI가 BERT 분석 결과를 사용합니다.

## 주요 기능

- BERT 기반 위험 조항 이진 분류
- 계약서 텍스트 직접 입력
- `.txt` 계약서 파일 불러오기
- 조항 단위 분리 및 위험 조항 탐지
- 위험 유형, 근거 키워드, 설명, 권장 확인 사항 표시
- 위험도 점수와 카테고리별 통계 제공
- 로컬 BERT API 연동
- 분석 리포트 `.txt` 다운로드

## 문서

- [제품 명세](docs/SPEC.md)
- [기술 설계](docs/TECHNICAL_DESIGN.md)
- [개발 로그](docs/DEVELOPMENT_LOG.md)

## 주의

이 서비스는 법률 정보를 쉽게 이해하기 위한 보조 도구입니다. 분석 결과는 법률 자문이 아니며, 실제 계약 체결 전에는 변호사 등 전문가의 검토가 필요합니다.
