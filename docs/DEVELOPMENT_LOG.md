# 개발 로그

## 2026-06-04

### 결정 사항

- 빈 프로젝트에서 정적 웹 MVP로 시작한다.
- 사용자가 제공한 연구 주제를 제품 명세로 구조화한다.
- 실제 BERT 학습은 추후 단계로 두고, 현재 앱은 규칙 기반 위험 탐지기로 구현한다.
- 앱은 서버 없이 `index.html`을 열어 실행할 수 있게 한다.

### 구현 범위

- `README.md` 작성
- `docs/SPEC.md` 작성
- `docs/TECHNICAL_DESIGN.md` 작성
- `docs/DEVELOPMENT_LOG.md` 작성
- 계약서 입력 UI 구현
- 조항 단위 분석 로직 구현
- 위험도 점수 및 리포트 UI 구현
- 리포트 다운로드 기능 구현

### 다음 단계

- PDF, DOCX, HWP 업로드 파서 추가
- BERT 학습용 데이터셋 구축
- Python 학습 스크립트 추가
- FastAPI 기반 추론 서버 추가
- 사용자 피드백 기반 위험 유형 세분화

## 2026-06-04 추가 작업

### 결정 사항

- 실제 BERT 파인튜닝 구조를 추가한다.
- 기본 모델은 한국어 계약 문장 처리에 맞춰 `klue/bert-base`를 사용한다.
- 데이터셋은 `data/contract_clauses_labeled.csv`에 조항, 라벨, 위험 유형 형태로 저장한다.
- 웹 UI는 로컬 BERT API가 켜져 있으면 BERT 결과를 우선 사용한다.

### 추가 구현

- `requirements.txt`
- `data/contract_clauses_labeled.csv`
- `scripts/train_bert.py`
- `scripts/predict_bert.py`
- `scripts/serve_bert.py`
- `scripts/contract_nlp.py`
