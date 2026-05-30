# Finviz 섹터 분류 vs 본 분류기 비교

## 1. 섹터 체계 비교 (11개 동일, 명칭만 다름)

두 체계 모두 **11개 섹터**로 동일하며, Finviz는 GICS를 변형한 명칭을 쓴다.
본 분류기는 GICS 한국어 명칭을 쓴다. 1:1 매핑이 가능하다.

| 본 분류기 (GICS 한글) | Finviz 명칭 | 명칭 일치 |
|----------------------|-------------|:--------:|
| 정보기술 | Technology | 유사 |
| 커뮤니케이션서비스 | Communication Services | ✅ |
| 헬스케어 | Healthcare | ✅ |
| 금융 | Financial | 유사 (단/복수) |
| 경기소비재 | **Consumer Cyclical** | ❌ 명칭 다름 |
| 필수소비재 | **Consumer Defensive** | ❌ 명칭 다름 |
| 산업재 | Industrials | ✅ |
| 소재 | **Basic Materials** | ❌ 명칭 다름 |
| 에너지 | Energy | ✅ |
| 유틸리티 | Utilities | ✅ |
| 부동산 | Real Estate | ✅ |

### 핵심 명칭 차이
- **경기소비재 = Consumer Cyclical** (경기민감 = 경기순환)
- **필수소비재 = Consumer Defensive** (필수재 = 방어주)
- **소재 = Basic Materials** (Finviz는 "Basic" 접두어)
- **금융**: Finviz "Financial"(단수) vs GICS "Financials"(복수)

## 2. 종목 분류 일치도 (주요 65개 검증)

- **일치율: 97% (63/65)**
- 불일치 2건은 모두 **2023년 GICS 개편**으로 이동한 종목이었음 → 교정 완료

| 종목 | 교정 전 (본 분류) | Finviz (정답) | 교정 후 |
|------|------------------|--------------|---------|
| TGT (Target) | 경기소비재 | Consumer Defensive | 필수소비재 ✅ |
| ADP | 정보기술 | Industrials | 산업재 ✅ |

### 2023 GICS 개편 반영 사항 (Finviz도 반영)
- **Visa, Mastercard**: Technology → **Financial** (이미 본 분류기 반영됨)
- **Target, Dollar General**: Consumer Cyclical → **Consumer Defensive** (교정 완료)
- **ADP**: Technology → **Industrials** (교정 완료)

## 3. 서브섹터(Industry) 비교

Finviz는 섹터 아래 **약 145개 Industry**를 둔다 (예: Technology 아래
Semiconductors, Software-Infrastructure, Software-Application, Consumer Electronics 등).
본 분류기의 SubSector는 한국 시장 실무 기준 **28개**로, Finviz Industry보다 거칠다.

| 본 분류기 SubSector | 대응 Finviz Industry (예시) |
|--------------------|---------------------------|
| 반도체 | Semiconductors, Semiconductor Equipment & Materials |
| 소프트웨어/IT서비스 | Software-Infrastructure, Software-Application, Information Technology Services |
| IT하드웨어 | Consumer Electronics, Communication Equipment, Computer Hardware |
| 바이오 | Biotechnology |
| 제약 | Drug Manufacturers-General, Drug Manufacturers-Specialty |
| 의료기기/진단 | Medical Devices, Diagnostics & Research, Medical Instruments |
| 은행 | Banks-Regional, Banks-Diversified |
| 증권 | Capital Markets, Asset Management, Credit Services |
| 보험 | Insurance-Property & Casualty, Insurance-Life 등 |
| 방산/항공우주 | Aerospace & Defense |
| 자동차/부품 | Auto Manufacturers, Auto Parts |

### 차이
- Finviz Industry가 **5배 이상 세분화**됨 (예: 은행을 Regional/Diversified로 분리)
- 본 분류기는 박병창식 "테마 매매" 단위에 맞춰 굵게 묶음
- 반도체를 별도 SubSector로 둔 것은 양쪽 다 동일 (Finviz도 Semiconductors 독립)

## 4. 결론

| 항목 | 평가 |
|------|------|
| 섹터 개수 | 동일 (11개) |
| 섹터 명칭 | 4개 명칭만 다름 (Consumer Cyclical/Defensive, Basic Materials, Financial) |
| 주요 종목 일치율 | 97% → 교정 후 100% |
| 서브섹터 세분화 | Finviz가 5배 세밀 (145 vs 28) |
| 호환성 | GICS_TO_FINVIZ 매핑으로 1:1 변환 가능 |

본 분류기는 Finviz와 **섹터 레벨에서 사실상 호환**된다.
서브섹터는 의도적으로 거칠게 묶었으므로(테마 매매용), 필요시 Finviz Industry로
세분화하는 매핑을 추가하면 된다.
