const riskRules = [
  {
    category: "과도한 위약금",
    severity: "high",
    weight: 24,
    keywords: ["위약금", "손해배상", "배상금", "벌금", "지체상금", "일체의 손해"],
    explanation: "해지나 의무 불이행 시 금전 부담이 크게 발생할 수 있습니다.",
    questions: ["금액 산정 기준이 명확한가?", "실제 손해보다 과도한 금액은 아닌가?", "상대방도 같은 수준의 책임을 지는가?"],
  },
  {
    category: "자동 연장",
    severity: "medium",
    weight: 16,
    keywords: ["자동 연장", "자동 갱신", "갱신되는 것으로 본다", "통지하지 않는 경우", "동일 조건으로 연장"],
    explanation: "사용자가 종료 의사를 놓치면 원하지 않는 계약이 계속될 수 있습니다.",
    questions: ["해지 통지 기한이 충분한가?", "자동 연장 전 별도 안내가 있는가?", "연장 후 해지 방법이 명확한가?"],
  },
  {
    category: "책임 면책",
    severity: "high",
    weight: 22,
    keywords: ["책임을 지지 않는다", "면책", "배상하지 않는다", "책임이 없다", "어떠한 책임도", "손해에 대하여 책임"],
    explanation: "상대방의 책임이 과도하게 제한되면 손해가 발생해도 구제받기 어려울 수 있습니다.",
    questions: ["고의 또는 중대한 과실까지 면책되는가?", "손해 발생 시 보상 절차가 있는가?", "책임 제한 범위가 구체적인가?"],
  },
  {
    category: "일방적 변경",
    severity: "high",
    weight: 20,
    keywords: ["임의로 변경", "사전 통지 없이", "일방적으로 변경", "변경할 수 있다", "회사 사정에 따라", "별도 동의 없이"],
    explanation: "계약 조건이 한쪽 당사자에게 유리하게 바뀔 수 있습니다.",
    questions: ["변경 시 사전 통지와 동의 절차가 있는가?", "변경을 거부할 권리가 있는가?", "변경 가능한 범위가 제한되어 있는가?"],
  },
  {
    category: "일방적 해지",
    severity: "medium",
    weight: 17,
    keywords: ["즉시 해지", "언제든지 해지", "일방적으로 해지", "계약을 해제할 수 있다", "통보만으로 해지"],
    explanation: "상대방이 계약을 쉽게 종료할 수 있으면 대금, 업무, 거주 안정성이 흔들릴 수 있습니다.",
    questions: ["해지 사유가 구체적인가?", "해지 전 시정 기회가 있는가?", "해지 시 정산 기준이 명확한가?"],
  },
  {
    category: "권리 귀속",
    severity: "medium",
    weight: 15,
    keywords: ["모든 권리", "권리가 귀속", "저작권", "지식재산권", "양도한다", "무상으로 사용"],
    explanation: "결과물이나 권리가 예상보다 넓게 이전될 수 있습니다.",
    questions: ["이전되는 권리 범위가 명확한가?", "대가가 권리 이전 범위에 비례하는가?", "포트폴리오 사용 가능 여부가 정해져 있는가?"],
  },
  {
    category: "지급 지연",
    severity: "medium",
    weight: 14,
    keywords: ["검수 후 지급", "사정에 따라 지급", "지급을 보류", "추후 지급", "정산 후 지급", "지급하지 않을 수 있다"],
    explanation: "대금 지급 시점이 불명확하면 현금 흐름과 분쟁 위험이 커질 수 있습니다.",
    questions: ["검수 기간이 정해져 있는가?", "지급 기한이 날짜로 명확한가?", "보류 사유와 이의 제기 절차가 있는가?"],
  },
  {
    category: "경업 금지",
    severity: "high",
    weight: 21,
    keywords: ["경업 금지", "동종 업계", "취업 금지", "거래 금지", "영업 금지", "경쟁 업체"],
    explanation: "계약 종료 후 직업 선택이나 영업 활동이 제한될 수 있습니다.",
    questions: ["제한 기간과 지역이 합리적인가?", "보상 조항이 있는가?", "제한 대상 업무가 과도하게 넓지 않은가?"],
  },
  {
    category: "관할 및 분쟁",
    severity: "low",
    weight: 10,
    keywords: ["전속 관할", "관할 법원", "중재", "소송", "분쟁은", "관할로 한다"],
    explanation: "분쟁이 생겼을 때 사용자가 불리한 장소나 절차를 따라야 할 수 있습니다.",
    questions: ["관할지가 사용자에게 과도하게 불리하지 않은가?", "중재 절차와 비용을 이해했는가?", "분쟁 해결 절차가 균형적인가?"],
  },
];

const BERT_API_URL = "http://127.0.0.1:8000";
const sampleContract = `제1조 계약 기간은 2026년 7월 1일부터 2027년 6월 30일까지 1년으로 한다.

제2조 용역 대금은 결과물 검수 후 지급하며, 회사 사정에 따라 지급을 보류할 수 있다.

제3조 계약 해지 시 수급인은 위약금 500만 원을 지급하여야 하며, 이로 인한 일체의 손해를 배상한다.

제4조 회사는 서비스 운영상 필요한 경우 사전 통지 없이 계약 조건을 변경할 수 있다.

제5조 계약 종료 후 2년 동안 수급인은 동종 업계 또는 경쟁 업체와 거래할 수 없다.

제6조 본 계약과 관련한 분쟁은 서울중앙지방법원을 전속 관할 법원으로 한다.`;

const contractText = document.querySelector("#contractText");
const contractType = document.querySelector("#contractType");
const analyzeButton = document.querySelector("#analyzeButton");
const sampleButton = document.querySelector("#sampleButton");
const clearButton = document.querySelector("#clearButton");
const fileInput = document.querySelector("#fileInput");
const downloadButton = document.querySelector("#downloadButton");
const apiStatus = document.querySelector("#apiStatus");
const apiStatusText = document.querySelector("#apiStatusText");
const resultsList = document.querySelector("#resultsList");
const emptyState = document.querySelector("#emptyState");
const scoreValue = document.querySelector("#scoreValue");
const scoreRing = document.querySelector("#scoreRing");
const riskLevel = document.querySelector("#riskLevel");
const summaryText = document.querySelector("#summaryText");
const totalClauses = document.querySelector("#totalClauses");
const riskClauses = document.querySelector("#riskClauses");
const topCategory = document.querySelector("#topCategory");
const categoryList = document.querySelector("#categoryList");

let lastReport = null;
let bertApiAvailable = false;

function normalizeText(text) {
  return text
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitIntoClauses(text) {
  const normalized = normalizeText(text);
  if (!normalized) return [];

  const lines = normalized
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  const clauses = [];
  let buffer = "";

  lines.forEach((line) => {
    const startsNewClause = /^(제\s*\d+\s*조|\d+\.|\(\d+\)|[가-하]\.)/.test(line);
    if (startsNewClause && buffer) {
      clauses.push(buffer.trim());
      buffer = line;
      return;
    }

    if (buffer) {
      buffer += " " + line;
    } else {
      buffer = line;
    }
  });

  if (buffer) clauses.push(buffer.trim());

  if (clauses.length <= 1) {
    return normalized
      .split(/(?<=[.다])\s+(?=(제\s*\d+\s*조|\d+\.|\(\d+\)|[가-하]\.|[가-힣A-Za-z]))/)
      .map((clause) => clause.trim())
      .filter((clause) => clause.length > 8);
  }

  return clauses;
}

function analyzeClause(text, index) {
  const matches = riskRules
    .map((rule) => {
      const evidence = rule.keywords.filter((keyword) => text.includes(keyword));
      return evidence.length ? { ...rule, evidence } : null;
    })
    .filter(Boolean);

  if (!matches.length) {
    return {
      id: `clause-${index + 1}`,
      index: index + 1,
      text,
      risk: false,
      category: "일반 조항",
      severity: "low",
      score: 0,
      evidence: [],
      explanation: "현재 기준에서는 주요 위험 키워드가 발견되지 않았습니다.",
      questions: ["계약 목적, 기간, 대금 등 기본 조건이 명확한지 확인하세요."],
    };
  }

  const strongest = matches.sort((a, b) => b.weight - a.weight)[0];
  const evidence = [...new Set(matches.flatMap((match) => match.evidence))];
  const score = Math.min(100, matches.reduce((sum, match) => sum + match.weight, 0) + evidence.length * 4);

  return {
    id: `clause-${index + 1}`,
    index: index + 1,
    text,
    risk: true,
    category: strongest.category,
    severity: score >= 42 || strongest.severity === "high" ? "high" : strongest.severity,
    score,
    evidence,
    explanation: strongest.explanation,
    questions: strongest.questions,
  };
}

function analyzeContract(text) {
  const clauses = splitIntoClauses(text);
  const analyzed = clauses.map(analyzeClause);
  const risky = analyzed.filter((clause) => clause.risk);
  const categoryCounts = risky.reduce((acc, clause) => {
    acc[clause.category] = (acc[clause.category] || 0) + 1;
    return acc;
  }, {});

  const rawScore = risky.reduce((sum, clause) => sum + clause.score, 0);
  const riskRatio = clauses.length ? risky.length / clauses.length : 0;
  const score = clauses.length ? Math.min(100, Math.round(rawScore / Math.max(1, clauses.length) + riskRatio * 45)) : 0;
  const top = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1])[0];

  return {
    source: "rule",
    contractType: contractType.value,
    score,
    level: getRiskLevel(score),
    clauses: analyzed,
    riskyCount: risky.length,
    categoryCounts,
    topCategory: top ? top[0] : "-",
    generatedAt: new Date().toLocaleString("ko-KR"),
  };
}

async function checkBertApi() {
  try {
    const response = await fetch(`${BERT_API_URL}/health`, { method: "GET" });
    bertApiAvailable = response.ok;
  } catch {
    bertApiAvailable = false;
  }

  apiStatus.classList.toggle("offline", !bertApiAvailable);
  apiStatusText.textContent = bertApiAvailable ? "BERT 모델 연결됨" : "BERT API 미연결";
}

async function analyzeWithBert(text) {
  const response = await fetch(`${BERT_API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      contractType: contractType.value,
    }),
  });

  if (!response.ok) {
    throw new Error(`BERT API error: ${response.status}`);
  }

  const report = await response.json();
  return {
    ...report,
    generatedAt: new Date().toLocaleString("ko-KR"),
  };
}

function getRiskLevel(score) {
  if (score >= 60) return { label: "높은 위험", tone: "high" };
  if (score >= 30) return { label: "주의 필요", tone: "medium" };
  if (score > 0) return { label: "낮은 위험", tone: "low" };
  return { label: "위험 낮음", tone: "low" };
}

function renderReport(report) {
  lastReport = report;
  downloadButton.disabled = report.clauses.length === 0;

  scoreValue.textContent = report.score;
  const color = report.level.tone === "high" ? "var(--danger)" : report.level.tone === "medium" ? "var(--warning)" : "var(--safe)";
  scoreRing.style.background = `radial-gradient(circle at center, #fff 58%, transparent 59%), conic-gradient(${color} ${report.score * 3.6}deg, #d9e2ec 0deg)`;
  riskLevel.textContent = report.level.label;
  riskLevel.style.color = color;

  totalClauses.textContent = report.clauses.length;
  riskClauses.textContent = report.riskyCount;
  topCategory.textContent = report.topCategory;

  const sourceLabel = report.source === "bert" ? "BERT 모델" : "규칙 기반 임시 분석";

  if (!report.clauses.length) {
    summaryText.textContent = "분석할 조항이 없습니다. 계약서 내용을 입력하세요.";
  } else if (report.riskyCount) {
    summaryText.textContent = `${sourceLabel} 기준으로 ${report.clauses.length}개 조항 중 ${report.riskyCount}개 조항에서 위험 가능성이 발견되었습니다. 표시된 질문을 기준으로 계약 전 확인이 필요합니다.`;
  } else {
    summaryText.textContent = `${sourceLabel} 기준으로 주요 위험 조항은 발견되지 않았습니다. 다만 실제 계약 전 핵심 조건과 법적 효과는 별도로 확인하세요.`;
  }

  renderCategories(report.categoryCounts);
  renderClauses(report.clauses);
}

function renderCategories(counts) {
  categoryList.innerHTML = "";
  const entries = Object.entries(counts);

  if (!entries.length) {
    const chip = document.createElement("span");
    chip.className = "category-chip";
    chip.textContent = "탐지된 위험 유형 없음";
    categoryList.appendChild(chip);
    return;
  }

  entries
    .sort((a, b) => b[1] - a[1])
    .forEach(([category, count]) => {
      const chip = document.createElement("span");
      chip.className = "category-chip";
      chip.textContent = `${category} ${count}`;
      categoryList.appendChild(chip);
    });
}

function renderClauses(clauses) {
  resultsList.innerHTML = "";
  emptyState.style.display = clauses.length ? "none" : "grid";

  clauses.forEach((clause) => {
    const article = document.createElement("article");
    article.className = `clause-card ${clause.severity}`;

    const header = document.createElement("div");
    header.className = "clause-header";
    header.innerHTML = `
      <span class="clause-title">조항 ${clause.index} · ${clause.category}</span>
      <span class="badge ${clause.severity}">${getSeverityLabel(clause)}</span>
    `;

    const text = document.createElement("p");
    text.className = "clause-text";
    text.innerHTML = highlightEvidence(clause.text, clause.evidence);

    const detail = document.createElement("div");
    detail.className = "clause-detail";
    detail.innerHTML = `
      <div class="detail-block">
        <h3>탐지 이유</h3>
        <p>${clause.explanation}</p>
      </div>
      <div class="detail-block">
        <h3>확인 질문</h3>
        <ul>${clause.questions.map((question) => `<li>${question}</li>`).join("")}</ul>
      </div>
    `;

    article.append(header, text, detail);
    resultsList.appendChild(article);
  });
}

function getSeverityLabel(clause) {
  if (!clause.risk) return "일반";
  if (clause.severity === "high") return "위험 높음";
  if (clause.severity === "medium") return "주의";
  return "낮음";
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function highlightEvidence(text, evidence) {
  let escaped = escapeHtml(text);
  evidence.forEach((keyword) => {
    const safeKeyword = escapeHtml(keyword);
    escaped = escaped.replaceAll(safeKeyword, `<mark>${safeKeyword}</mark>`);
  });
  return escaped;
}

function buildReportText(report) {
  const lines = [
    "계약서 위험 조항 탐지 AI 분석 리포트",
    `생성 시각: ${report.generatedAt}`,
    `계약 유형: ${report.contractType}`,
    `분석 방식: ${report.source === "bert" ? "BERT 모델" : "규칙 기반 임시 분석"}`,
    `위험도 점수: ${report.score}`,
    `위험 수준: ${report.level.label}`,
    `전체 조항: ${report.clauses.length}`,
    `위험 조항: ${report.riskyCount}`,
    "",
    "조항별 분석",
  ];

  report.clauses.forEach((clause) => {
    lines.push("");
    lines.push(`[조항 ${clause.index}] ${clause.category} / ${getSeverityLabel(clause)}`);
    lines.push(clause.text);
    lines.push(`탐지 이유: ${clause.explanation}`);
    lines.push(`근거 표현: ${clause.evidence.length ? clause.evidence.join(", ") : "없음"}`);
    lines.push(`확인 질문: ${clause.questions.join(" / ")}`);
  });

  lines.push("");
  lines.push("주의: 본 리포트는 일반 정보 제공용이며 법률 자문이 아닙니다.");
  return lines.join("\n");
}

function downloadReport() {
  if (!lastReport) return;

  const blob = new Blob([buildReportText(lastReport)], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "contract-risk-report.txt";
  link.click();
  URL.revokeObjectURL(url);
}

analyzeButton.addEventListener("click", async () => {
  analyzeButton.disabled = true;
  analyzeButton.textContent = "분석 중";
  try {
    if (bertApiAvailable) {
      renderReport(await analyzeWithBert(contractText.value));
    } else {
      renderReport(analyzeContract(contractText.value));
    }
  } catch {
    await checkBertApi();
    renderReport(analyzeContract(contractText.value));
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "위험 조항 분석";
  }
});

sampleButton.addEventListener("click", async () => {
  contractText.value = sampleContract;
  if (bertApiAvailable) {
    renderReport(await analyzeWithBert(contractText.value));
  } else {
    renderReport(analyzeContract(contractText.value));
  }
});

clearButton.addEventListener("click", () => {
  contractText.value = "";
  lastReport = null;
  renderReport({ score: 0, level: getRiskLevel(0), clauses: [], riskyCount: 0, categoryCounts: {}, topCategory: "-" });
  downloadButton.disabled = true;
});

fileInput.addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  contractText.value = await file.text();
  if (bertApiAvailable) {
    renderReport(await analyzeWithBert(contractText.value));
  } else {
    renderReport(analyzeContract(contractText.value));
  }
  fileInput.value = "";
});

downloadButton.addEventListener("click", downloadReport);

renderReport({ source: "rule", score: 0, level: getRiskLevel(0), clauses: [], riskyCount: 0, categoryCounts: {}, topCategory: "-" });
checkBertApi();
