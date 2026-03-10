#!/bin/bash

ANALYZE_CMD="python main.py analyze --save-chart --save-report"

# ── 한국 주식 분석 함수 ─────────────────────
analyze_ko() {
    echo "=== 한국 KOSPI 주식 분석을 시작합니다 ==="
    $ANALYZE_CMD "005930.KS"   # 삼성전자
    $ANALYZE_CMD "000660.KS"   # SK하이닉스
    $ANALYZE_CMD "005380.KS"   # 현대차
    $ANALYZE_CMD "000270.KS"   # 기아자동차
    $ANALYZE_CMD "373220.KS"   # LG에너지솔루션
    $ANALYZE_CMD "402340.KS"   # SK스퀘어
    $ANALYZE_CMD "207940.KS"   # 삼성바이오로직스
    $ANALYZE_CMD "034020.KS"   # 두산에너빌리티
    $ANALYZE_CMD "012450.KS"   # 한화에어로스페이스
    $ANALYZE_CMD "329180.KS"   # HD현대중공업
    $ANALYZE_CMD "028260.KS"   # 삼성물산
    $ANALYZE_CMD "105560.KS"   # KB금융
    $ANALYZE_CMD "068270.KS"   # 셀트리온
    $ANALYZE_CMD "032830.KS"   # 삼성생명
    $ANALYZE_CMD "012330.KS"   # 현대모비스
    $ANALYZE_CMD "042660.KS"   # 한화오션
    $ANALYZE_CMD "009150.KS"   # 삼성전기
    $ANALYZE_CMD "035720.KS"   # 카카오
    $ANALYZE_CMD "035420.KS"   # NAVER
    $ANALYZE_CMD "005935.KS"   # 삼성전자우
    $ANALYZE_CMD "055550.KS"   # 신한지주
    $ANALYZE_CMD "010130.KS"   # 고려아연
    $ANALYZE_CMD "006800.KS"   # 미래에셋증권
    $ANALYZE_CMD "267260.KS"   # HD현대일렉트릭
    $ANALYZE_CMD "015760.KS"   # 한국전력
    $ANALYZE_CMD "006400.KS"   # 삼성SDI
    $ANALYZE_CMD "086790.KS"   # 하나금융지주
    $ANALYZE_CMD "005490.KS"   # POSCO홀딩스
    $ANALYZE_CMD "009540.KS"   # HD한국조선해양
    $ANALYZE_CMD "042700.KS"   # 한미반도체
    $ANALYZE_CMD "051910.KS"   # LG화학
    $ANALYZE_CMD "034730.KS"   # SK
    $ANALYZE_CMD "316140.KS"   # 우리금융지주
    $ANALYZE_CMD "298040.KS"   # 효성중공업
    $ANALYZE_CMD "010140.KS"   # 삼성중공업
    $ANALYZE_CMD "000810.KS"   # 삼성화재
    $ANALYZE_CMD "066570.KS"   # LG전자
    $ANALYZE_CMD "010120.KS"   # LS ELECTRIC
    $ANALYZE_CMD "267250.KS"   # HD현대
    $ANALYZE_CMD "138040.KS"   # 메리츠금융지주
    $ANALYZE_CMD "003670.KS"   # 포스코퓨처엠
    $ANALYZE_CMD "086280.KS"   # 현대글로비스
    $ANALYZE_CMD "096770.KS"   # SK이노베이션
    $ANALYZE_CMD "272210.KS"   # 한화시스템
    $ANALYZE_CMD "000150.KS"   # 두산
    $ANALYZE_CMD "024110.KS"   # 기업은행
    $ANALYZE_CMD "011200.KS"   # HMM
    $ANALYZE_CMD "069500.KS"   # KODEX 200
    $ANALYZE_CMD "033780.KS"   # KT&G

    $ANALYZE_CMD "064350.KS"   # 현대로템
    $ANALYZE_CMD "079550.KS"   # LIG넥스원
    $ANALYZE_CMD "047810.KS"   # 한국항공우주
    $ANALYZE_CMD "000720.KS"   # 현대건설
    $ANALYZE_CMD "017670.KS"   # SK텔레콤
    $ANALYZE_CMD "352820.KS"   # 하이브
    $ANALYZE_CMD "030200.KS"   # KT
    $ANALYZE_CMD "010950.KS"   # S-Oil
    $ANALYZE_CMD "003550.KS"   # LG
    $ANALYZE_CMD "0126Z0.KS"   # 삼성에피스홀딩스
    $ANALYZE_CMD "005830.KS"   # DB손해보험
    $ANALYZE_CMD "047050.KS"   # 포스코인터내셔널
    $ANALYZE_CMD "071050.KS"   # 한국금융지주
    $ANALYZE_CMD "018260.KS"   # 삼성에스디에스
    $ANALYZE_CMD "039490.KS"   # 키움증권
    $ANALYZE_CMD "323410.KS"   # 카카오뱅크
    $ANALYZE_CMD "005940.KS"   # NH투자증권
    $ANALYZE_CMD "278470.KS"   # 에이피알
    $ANALYZE_CMD "307950.KS"   # 현대오토에버
    $ANALYZE_CMD "259960.KS"   # 크래프톤
    $ANALYZE_CMD "000880.KS"   # 한화
    $ANALYZE_CMD "003490.KS"   # 대한항공
    $ANALYZE_CMD "009830.KS"   # 한화솔루션
    $ANALYZE_CMD "016360.KS"   # 삼성증권
    $ANALYZE_CMD "007660.KS"   # 이수페타시스
    $ANALYZE_CMD "377300.KS"   # 카카오페이
    $ANALYZE_CMD "180640.KS"   # 한진칼
    $ANALYZE_CMD "326030.KS"   # SK바이오팜
    $ANALYZE_CMD "003230.KS"   # 삼양식품
    $ANALYZE_CMD "000100.KS"   # 유한양행
    $ANALYZE_CMD "006260.KS"   # LS
    $ANALYZE_CMD "090430.KS"   # 아모레퍼시픽
    $ANALYZE_CMD "443060.KS"   # HD현대마린솔루션
    $ANALYZE_CMD "161390.KS"   # 한국타이어앤테크놀로지
    $ANALYZE_CMD "029780.KS"   # 삼성카드
    $ANALYZE_CMD "128940.KS"   # 한미약품
    $ANALYZE_CMD "028050.KS"   # 삼성E&A
    $ANALYZE_CMD "032640.KS"   # LG유플러스
    $ANALYZE_CMD "011070.KS"   # LG이노텍
    $ANALYZE_CMD "064400.KS"   # LG씨엔에스
    $ANALYZE_CMD "078930.KS"   # GS
    $ANALYZE_CMD "267270.KS"   # HD건설기계
    $ANALYZE_CMD "052690.KS"   # 한전기술
    $ANALYZE_CMD "454910.KS"   # 두산로보틱스
    $ANALYZE_CMD "138930.KS"   # BNK금융지주
    $ANALYZE_CMD "241560.KS"   # 두산밥캣
    $ANALYZE_CMD "175330.KS"   # JB금융지주
    $ANALYZE_CMD "021240.KS"   # 코웨이
    $ANALYZE_CMD "001040.KS"   # CJ
    $ANALYZE_CMD "004020.KS"   # 현대제철
    $ANALYZE_CMD "022100.KS"   # 포스코DX
    $ANALYZE_CMD "271560.KS"   # 오리온
    $ANALYZE_CMD "002380.KS"   # KCC
    $ANALYZE_CMD "066970.KS"   # 엘앤에프
    $ANALYZE_CMD "036570.KS"   # 엔씨소프트
    $ANALYZE_CMD "062040.KS"   # 산일전기
    $ANALYZE_CMD "251270.KS"   # 넷마블
    $ANALYZE_CMD "489790.KS"   # 한화비전
    $ANALYZE_CMD "111770.KS"   # 영원무역
    $ANALYZE_CMD "082740.KS"   # 한화엔진
    $ANALYZE_CMD "439260.KS"   # 대한조선
    $ANALYZE_CMD "011790.KS"   # SKC
    $ANALYZE_CMD "000990.KS"   # DB하이텍
    $ANALYZE_CMD "103590.KS"   # 일진전기
    $ANALYZE_CMD "035250.KS"   # 강원랜드
    $ANALYZE_CMD "031210.KS"   # 서울보증보험
    $ANALYZE_CMD "051900.KS"   # LG생활건강
    $ANALYZE_CMD "012510.KS"   # 더존비즈온
    $ANALYZE_CMD "014680.KS"   # 한솔케미칼
    $ANALYZE_CMD "302440.KS"   # SK바이오사이언스
    $ANALYZE_CMD "036460.KS"   # 한국가스공사
    $ANALYZE_CMD "017800.KS"   # 현대엘리베이터
    $ANALYZE_CMD "103140.KS"   # 풍산
    $ANALYZE_CMD "004990.KS"   # 롯데지주
    $ANALYZE_CMD "011170.KS"   # 롯데케미칼
    $ANALYZE_CMD "004170.KS"   # 신세계
    $ANALYZE_CMD "001720.KS"   # 신영증권
    $ANALYZE_CMD "011780.KS"   # 금호석유화학
    $ANALYZE_CMD "012750.KS"   # 에스원
    $ANALYZE_CMD "457190.KS"   # 이수스페셜티케미컬
    $ANALYZE_CMD "005850.KS"   # 에스엘
    $ANALYZE_CMD "009970.KS"   # 영원무역홀딩스
    $ANALYZE_CMD "097950.KS"   # CJ제일제당
    $ANALYZE_CMD "009420.KS"   # 한올바이오파마
    $ANALYZE_CMD "010060.KS"   # OCI홀딩스
    $ANALYZE_CMD "001450.KS"   # 현대해상
    $ANALYZE_CMD "139130.KS"   # iM금융지주
    $ANALYZE_CMD "023530.KS"   # 롯데쇼핑
    $ANALYZE_CMD "000120.KS"   # CJ대한통운
    $ANALYZE_CMD "008930.KS"   # 한미사이언스
    $ANALYZE_CMD "071970.KS"   # HD현대마린엔진
    $ANALYZE_CMD "336260.KS"   # 두산퓨얼셀
    $ANALYZE_CMD "085620.KS"   # 미래에셋생명
    $ANALYZE_CMD "081660.KS"   # 미스토홀딩스
    $ANALYZE_CMD "139480.KS"   # 이마트
    $ANALYZE_CMD "026960.KS"   # 동서
    $ANALYZE_CMD "204320.KS"   # HL만도
    $ANALYZE_CMD "003690.KS"   # 코리안리
    $ANALYZE_CMD "051600.KS"   # 한전KPS
    $ANALYZE_CMD "011210.KS"   # 현대위아
    $ANALYZE_CMD "000240.KS"   # 한국앤컴퍼니
    $ANALYZE_CMD "004800.KS"   # 효성
    $ANALYZE_CMD "383220.KS"   # F&F
    $ANALYZE_CMD "004370.KS"   # 농심
    $ANALYZE_CMD "030000.KS"   # 제일기획
    $ANALYZE_CMD "005440.KS"   # 현대지에프홀딩스
    $ANALYZE_CMD "023590.KS"   # 다우기술
    $ANALYZE_CMD "001430.KS"   # 세아베스틸지주
    $ANALYZE_CMD "112610.KS"   # 씨에스윈드
    $ANALYZE_CMD "017960.KS"   # 한국카본
    $ANALYZE_CMD "002790.KS"   # 아모레퍼시픽홀딩스
    $ANALYZE_CMD "020150.KS"   # 롯데에너지머티리얼즈
    $ANALYZE_CMD "018670.KS"   # SK가스
    $ANALYZE_CMD "003540.KS"   # 대신증권
    $ANALYZE_CMD "069960.KS"   # 현대백화점
    $ANALYZE_CMD "282330.KS"   # BGF리테일
    $ANALYZE_CMD "069620.KS"   # 대웅제약
    $ANALYZE_CMD "361610.KS"   # SK아이이테크놀로지
    $ANALYZE_CMD "192820.KS"   # 코스맥스
    $ANALYZE_CMD "483650.KS"   # 달바글로벌
    $ANALYZE_CMD "462870.KS"   # 시프트업
    $ANALYZE_CMD "006280.KS"   # 녹십자
    $ANALYZE_CMD "375500.KS"   # DL이앤씨
    $ANALYZE_CMD "120110.KS"   # 코오롱인더
    $ANALYZE_CMD "005070.KS"   # 코스모신소재
    $ANALYZE_CMD "073240.KS"   # 금호타이어
    $ANALYZE_CMD "022100.KS"   # 동원산업
    $ANALYZE_CMD "006360.KS"   # GS건설
    $ANALYZE_CMD "000500.KS"   # 가온전선
    $ANALYZE_CMD "161890.KS"   # 한국콜마
    $ANALYZE_CMD "008770.KS"   # 호텔신라
    $ANALYZE_CMD "003570.KS"   # SNT다이내믹스
    $ANALYZE_CMD "007070.KS"   # GS리테일
    $ANALYZE_CMD "034230.KS"   # 파라다이스
    $ANALYZE_CMD "001120.KS"   # LX인터내셔널
    $ANALYZE_CMD "032350.KS"   # 롯데관광개발
    $ANALYZE_CMD "007310.KS"   # 오뚜기
    $ANALYZE_CMD "007340.KS"   # DN오토모티브
    $ANALYZE_CMD "020560.KS"   # 아시아나항공
    $ANALYZE_CMD "030610.KS"   # 교보증권
    $ANALYZE_CMD "012630.KS"   # HDC
    $ANALYZE_CMD "001800.KS"   # 오리온홀딩스
    $ANALYZE_CMD "294870.KS"   # HDC현대산업개발
    $ANALYZE_CMD "298020.KS"   # 효성티앤씨
    $ANALYZE_CMD "003090.KS"   # 대웅
    $ANALYZE_CMD "003240.KS"   # 태광산업
    $ANALYZE_CMD "007810.KS"   # 코리아써키트
    $ANALYZE_CMD "229640.KS"   # LS에코에너지
    $ANALYZE_CMD "484870.KS"   # 엠앤씨솔루션
    $ANALYZE_CMD "300720.KS"   # 한일시멘트
    $ANALYZE_CMD "181710.KS"   # NHN
    $ANALYZE_CMD "077970.KS"   # STX엔진
  
    # ── 보유종목 ─────────────────────
    $ANALYZE_CMD "001680.KS"   # 대상
    $ANALYZE_CMD "005680.KS"   # 삼영전자
    $ANALYZE_CMD "007070.KS"   # GS리테일
    $ANALYZE_CMD "008490.KS"   # 서흥
    $ANALYZE_CMD "016580.KS"   # 환인제약
    $ANALYZE_CMD "040420.KQ"   # 정상제이엘에스

    # ── KOSDAQ 종목 ─────────────────────
    $ANALYZE_CMD "452430.KQ"   # 사피엔반도체
    $ANALYZE_CMD "298050.KS"   # HS효성첨단소재
    $ANALYZE_CMD "086520.KQ"   # 에코프로
    $ANALYZE_CMD "196170.KQ"   # 알테오젠
    $ANALYZE_CMD "247540.KQ"   # 에코프로비엠
    $ANALYZE_CMD "000250.KQ"   # 삼천당제약
    $ANALYZE_CMD "277810.KQ"   # 레인보우로보틱스
    $ANALYZE_CMD "298380.KQ"   # 에이비엘바이오
    $ANALYZE_CMD "950160.KQ"   # 코오롱티슈진
    $ANALYZE_CMD "058470.KQ"   # 리노공업
    $ANALYZE_CMD "214370.KQ"   # 케어젠
    $ANALYZE_CMD "141080.KQ"   # 리가켐바이오
    $ANALYZE_CMD "028300.KQ"   # HLB
    $ANALYZE_CMD "087010.KQ"   # 펩트론
    $ANALYZE_CMD "240810.KQ"   # 원익IPS
    $ANALYZE_CMD "310210.KQ"   # 보로노이
    $ANALYZE_CMD "039030.KQ"   # 이오테크닉스
    $ANALYZE_CMD "140410.KQ"   # 메지온
    $ANALYZE_CMD "108490.KQ"   # 로보티즈
    $ANALYZE_CMD "095340.KQ"   # ISC
    $ANALYZE_CMD "347850.KQ"   # 디앤디파마텍
    $ANALYZE_CMD "0009K0.KQ"   # 에임드바이오
    $ANALYZE_CMD "319400.KQ"   # 현대무벡스
    $ANALYZE_CMD "214150.KQ"   # 클래시스
    $ANALYZE_CMD "403870.KQ"   # HPSP
    $ANALYZE_CMD "226950.KQ"   # 올릭스
    $ANALYZE_CMD "214450.KQ"   # 파마리서치
    $ANALYZE_CMD "357780.KQ"   # 솔브레인
    $ANALYZE_CMD "263750.KQ"   # 편어비스
    $ANALYZE_CMD "145020.KQ"   # 휴젤
    $ANALYZE_CMD "058610.KQ"   # 에스피지
    $ANALYZE_CMD "237690.KQ"   # 에스티팜
    $ANALYZE_CMD "068760.KQ"   # 셀트리온제약
    $ANALYZE_CMD "084370.KQ"   # 유진테크
    $ANALYZE_CMD "440110.KQ"   # 파두
    $ANALYZE_CMD "083650.KQ"   # 비에이치아이
    $ANALYZE_CMD "032820.KQ"   # 우리기술
    $ANALYZE_CMD "005290.KQ"   # 동진쎄미켐
    $ANALYZE_CMD "475830.KQ"   # 오름테라퓨틱
    $ANALYZE_CMD "178320.KQ"   # 서진시스템
    $ANALYZE_CMD "030530.KQ"   # 원익홀딩스
    $ANALYZE_CMD "257720.KQ"   # 실리콘투
    $ANALYZE_CMD "036930.KQ"   # 주성엔지니어링
    $ANALYZE_CMD "041510.KQ"   # 에스엠
    $ANALYZE_CMD "064760.KQ"   # 티씨케이
    $ANALYZE_CMD "035900.KQ"   # JYP Ent.
    $ANALYZE_CMD "290650.KQ"   # 엘앤씨바이오
    $ANALYZE_CMD "323280.KQ"   # 태성
    $ANALYZE_CMD "067310.KQ"   # 하나마이크론
    $ANALYZE_CMD "491000.KQ"   # 리브스메드
    $ANALYZE_CMD "098460.KQ"   # 고영
    $ANALYZE_CMD "160190.KQ"   # 하이젠알앤엠
    $ANALYZE_CMD "263750.KQ"   # 펄어비스
    $ANALYZE_CMD "031980.KQ"   # 피에스케이홀딩스
    $ANALYZE_CMD "476830.KQ"   # 알지노믹스
    $ANALYZE_CMD "347700.KQ"   # 스피어
    $ANALYZE_CMD "222800.KQ"   # 심텍
    $ANALYZE_CMD "099320.KQ"   # 쎄트렉아이
    $ANALYZE_CMD "039200.KQ"   # 오스코텍
    $ANALYZE_CMD "140860.KQ"   # 파크시스템스
    $ANALYZE_CMD "101490.KQ"   # 에스앤에스텍
    $ANALYZE_CMD "319660.KQ"   # 피에스케이
    $ANALYZE_CMD "078600.KQ"   # 대주전자재료
    $ANALYZE_CMD "082270.KQ"   # 젬백스
    $ANALYZE_CMD "085660.KQ"   # 차바이오텍
    $ANALYZE_CMD "445680.KQ"   # 큐리옥스바이오시스템즈
    $ANALYZE_CMD "218410.KQ"   # RFHIC
    $ANALYZE_CMD "437730.KQ"   # 삼현
    $ANALYZE_CMD "065350.KQ"   # 신성델타테크
    $ANALYZE_CMD "458870.KQ"   # 씨어스테크놀로지
    $ANALYZE_CMD "456160.KQ"   # 지투지바이오
    $ANALYZE_CMD "115180.KQ"   # 큐리언트
    $ANALYZE_CMD "397030.KQ"   # 에이프릴바이오
    $ANALYZE_CMD "466100.KQ"   # 클로봇
    $ANALYZE_CMD "035760.KQ"   # CJ ENM
    $ANALYZE_CMD "195940.KQ"   # HK이노엔
    $ANALYZE_CMD "060370.KQ"   # LS마린솔루션
    $ANALYZE_CMD "095610.KQ"   # 테스
    $ANALYZE_CMD "388210.KQ"   # 씨엠티엑스
    $ANALYZE_CMD "348370.KQ"   # 엔켐
    $ANALYZE_CMD "189300.KQ"   # 인텔리안테크
    $ANALYZE_CMD "388720.KQ"   # 유일로보틱스
    $ANALYZE_CMD "131970.KQ"   # 두산테스나
    $ANALYZE_CMD "166090.KQ"   # 하나머티리얼즈
    $ANALYZE_CMD "127120.KQ"   # 제이에스링크
    $ANALYZE_CMD "007390.KQ"   # 네이처셀
    $ANALYZE_CMD "124500.KQ"   # 아이티센글로벌
    $ANALYZE_CMD "389470.KQ"   # 인벤티지랩
    $ANALYZE_CMD "122870.KQ"   # 와이지엔터테인먼트
    $ANALYZE_CMD "253450.KQ"   # 스튜디오드래곤
    $ANALYZE_CMD "171090.KQ"   # 선익시스템
    $ANALYZE_CMD "293490.KQ"   # 카카오게임즈
    $ANALYZE_CMD "096530.KQ"   # 씨젠
    $ANALYZE_CMD "137400.KQ"   # 피엔티
    $ANALYZE_CMD "056190.KQ"   # 에스에프에이
    $ANALYZE_CMD "131290.KQ"   # 티에스이
    $ANALYZE_CMD "376900.KQ"   # 로킷헬스케어
    $ANALYZE_CMD "036830.KQ"   # 솔브레인홀딩스
    $ANALYZE_CMD "183300.KQ"   # 코미코
    $ANALYZE_CMD "204270.KQ"   # 제이앤티씨
    $ANALYZE_CMD "161580.KQ"   # 필옵틱스
    $ANALYZE_CMD "328130.KQ"   # 루닛
    $ANALYZE_CMD "089970.KQ"   # 브이엠
    $ANALYZE_CMD "213420.KQ"   # 덕산네오룩스
    $ANALYZE_CMD "082920.KQ"   # 비츠로셀
    $ANALYZE_CMD "295310.KQ"   # 에이치브이엠
    $ANALYZE_CMD "074600.KQ"   # 원익QnC
    $ANALYZE_CMD "014620.KQ"   # 성광벤드
    $ANALYZE_CMD "358570.KQ"   # 지아이이노베이션
    $ANALYZE_CMD "032190.KQ"   # 다우데이타
    $ANALYZE_CMD "086900.KQ"   # 메디톡스
    $ANALYZE_CMD "052400.KQ"   # 코나아이
    $ANALYZE_CMD "376300.KQ"   # 디어유
    $ANALYZE_CMD "086450.KQ"   # 동국제약
    $ANALYZE_CMD "078160.KQ"   # 메디포스트
    $ANALYZE_CMD "126340.KQ"   # 비나텍
    $ANALYZE_CMD "476060.KQ"   # 온코닉테라퓨틱스
    $ANALYZE_CMD "420770.KQ"   # 기가비스
    $ANALYZE_CMD "348210.KQ"   # 넥스틴
    $ANALYZE_CMD "084110.KQ"   # 휴온스글로벌
    $ANALYZE_CMD "241710.KQ"   # 코스메카코리아
    $ANALYZE_CMD "448900.KQ"   # 한국피아이엠
    $ANALYZE_CMD "102710.KQ"   # 이엔에프테크놀로지
    $ANALYZE_CMD "121600.KQ"   # 나노신소재
    $ANALYZE_CMD "468530.KQ"   # 프로티나
    $ANALYZE_CMD "036810.KQ"   # 에프에스티
    $ANALYZE_CMD "044490.KQ"   # 태웅
    $ANALYZE_CMD "112040.KQ"   # 위메이드
    $ANALYZE_CMD "033500.KQ"   # 동성화인텍
    $ANALYZE_CMD "033100.KQ"   # 제룡전기
    $ANALYZE_CMD "102940.KQ"   # 코오롱생명과학
    $ANALYZE_CMD "067160.KQ"   # SOOP
    $ANALYZE_CMD "023160.KQ"   # 태광
    $ANALYZE_CMD "009520.KQ"   # 포스코엠텍
    $ANALYZE_CMD "475960.KQ"   # 토모큐브
    $ANALYZE_CMD "225570.KQ"   # 넥슨게임즈
    $ANALYZE_CMD "372320.KQ"   # 큐로셀
    $ANALYZE_CMD "214430.KQ"   # 아이쓰리시스템
    $ANALYZE_CMD "032500.KQ"   # 케이엠더블유
    $ANALYZE_CMD "053800.KQ"   # 안랩
    $ANALYZE_CMD "399720.KQ"   # 가온칩스
    $ANALYZE_CMD "211050.KQ"   # 인카금융서비스
    $ANALYZE_CMD "486990.KQ"   # 노타
    $ANALYZE_CMD "365340.KQ"   # 성일하이텍
    $ANALYZE_CMD "042000.KQ"   # 카페24
    $ANALYZE_CMD "042520.KQ"   # 한스바이오메드
    $ANALYZE_CMD "272290.KQ"   # 이녹스첨단소재
    $ANALYZE_CMD "090360.KQ"   # 로보스타
    $ANALYZE_CMD "336570.KQ"   # 원텍
    $ANALYZE_CMD "484590.KQ"   # 삼양컴텍
    $ANALYZE_CMD "053610.KQ"   # 프로텍
    $ANALYZE_CMD "287840.KQ"   # 인투셀
    $ANALYZE_CMD "015750.KQ"   # 성우하이텍
    $ANALYZE_CMD "460930.KQ"   # 현대힘스
    $ANALYZE_CMD "095660.KQ"   # 네오위즈
    $ANALYZE_CMD "251970.KQ"   # 펌텍코리아
    $ANALYZE_CMD "389650.KQ"   # 넥스트바이오메디컬
    $ANALYZE_CMD "119850.KQ"   # 지엔씨에너지
    $ANALYZE_CMD "104830.KQ"   # 원익머트리얼즈
    $ANALYZE_CMD "099190.KQ"   # 아이센스
    $ANALYZE_CMD "356860.KQ"   # 티엘비
    $ANALYZE_CMD "278280.KQ"   # 천보
    $ANALYZE_CMD "046890.KQ"   # 서울반도체
    $ANALYZE_CMD "083450.KQ"   # GST
    $ANALYZE_CMD "424870.KQ"   # 이뮨온시아
    $ANALYZE_CMD "200710.KQ"   # 에이디테크놀로지
    $ANALYZE_CMD "494120.KQ"   # 큐리오시스
    $ANALYZE_CMD "094170.KQ"   # 동운아나텍
    $ANALYZE_CMD "093320.KQ"   # 케이아이엔엑스
    $ANALYZE_CMD "045100.KQ"   # 한양이엔지
    $ANALYZE_CMD "036620.KQ"   # 감성코퍼레이션
    $ANALYZE_CMD "018290.KQ"   # 브이티
    $ANALYZE_CMD "039440.KQ"   # 에스티아이
    $ANALYZE_CMD "376270.KQ"   # HEM파마
    $ANALYZE_CMD "025320.KQ"   # 시노펙스
    $ANALYZE_CMD "230360.KQ"   # 에코마케팅
    $ANALYZE_CMD "425420.KQ"   # 티에프이
    $ANALYZE_CMD "215200.KQ"   # 메가스터디교육
    $ANALYZE_CMD "047920.KQ"   # HLB제약
    $ANALYZE_CMD "194480.KQ"   # 데브시스터즈
    $ANALYZE_CMD "025900.KQ"   # 동화기업
    $ANALYZE_CMD "101160.KQ"   # 월덱스
    $ANALYZE_CMD "030520.KQ"   # 한글과컴퓨터
    $ANALYZE_CMD "122640.KQ"   # 예스티
    $ANALYZE_CMD "059090.KQ"   # 미코
    $ANALYZE_CMD "488900.KQ"   # 비츠로넥스텍
    $ANALYZE_CMD "034950.KQ"   # 한국기업평가
    $ANALYZE_CMD "101730.KQ"   # 위메이드맥스
    $ANALYZE_CMD "228760.KQ"   # 지노믹트리
    $ANALYZE_CMD "168360.KQ"   # 펨트론
    $ANALYZE_CMD "117730.KQ"   # 티로보틱스
    $ANALYZE_CMD "107640.KQ"   # 한중엔시에스
    $ANALYZE_CMD "089010.KQ"   # 켐트로닉스
    $ANALYZE_CMD "069080.KQ"   # 웹젠
    $ANALYZE_CMD "053030.KQ"   # 바이넥스
    $ANALYZE_CMD "450950.KQ"   # 아스테라시스
    $ANALYZE_CMD "065660.KQ"   # 안트로젠
    $ANALYZE_CMD "058970.KQ"   # 엠로
    $ANALYZE_CMD "220100.KQ"   # 퓨쳐켐
    $ANALYZE_CMD "110990.KQ"   # 디아이티
    $ANALYZE_CMD "013030.KQ"   # 하이록코리아
    $ANALYZE_CMD "199800.KQ"   # 툴젠
    $ANALYZE_CMD "304360.KQ"   # 에스바이오메딕스
    $ANALYZE_CMD "394800.KQ"   # 쓰리빌리언
    $ANALYZE_CMD "455900.KQ"   # 엔젤로보틱스
    $ANALYZE_CMD "340570.KQ"   # 티앤엘
    $ANALYZE_CMD "078340.KQ"   # 컴투스
    $ANALYZE_CMD "086390.KQ"   # 유니테스트
    $ANALYZE_CMD "179900.KQ"   # 유티아이
    $ANALYZE_CMD "200670.KQ"   # 휴메딕스
    $ANALYZE_CMD "079940.KQ"   # 가비아
    $ANALYZE_CMD "114810.KQ"   # 한솔아이원스
    $ANALYZE_CMD "098070.KQ"   # 한텍
    echo "=== 한국 주식 분석 완료 ==="
}

# ── 미국 주식 분석 함수 ───────────────────────────
analyze_us() {
    echo "=== 미국 주식 분석을 시작합니다 ==="
    $ANALYZE_CMD "NVDA"        # NVIDIA Corporation
    $ANALYZE_CMD "AAPL"        # Apple Inc.
    $ANALYZE_CMD "GOOGL"       # Alphabet Inc.
    $ANALYZE_CMD "MSFT"        # Microsoft Corporation
    $ANALYZE_CMD "AMZN"        # Amazon.com, Inc.
    $ANALYZE_CMD "TSM"         # Taiwan Semiconductor Manufacturing Company Limited
    $ANALYZE_CMD "META"        # Meta Platforms, Inc.
    $ANALYZE_CMD "AVGO"        # Broadcom Inc.
    $ANALYZE_CMD "TSLA"        # Tesla, Inc.
    $ANALYZE_CMD "BRK-B"       # Berkshire Hathaway Inc.
    $ANALYZE_CMD "WMT"         # Walmart Inc.
    $ANALYZE_CMD "LLY"         # Eli Lilly and Company
    $ANALYZE_CMD "JPM"         # JPMorgan Chase & Co.
    $ANALYZE_CMD "AZN"         # AstraZeneca PLC
    $ANALYZE_CMD "XOM"         # Exxon Mobil Corporation
    $ANALYZE_CMD "V"           # Visa Inc.
    $ANALYZE_CMD "JNJ"         # Johnson & Johnson
    $ANALYZE_CMD "ASML"        # ASML Holding N.V.
    $ANALYZE_CMD "MU"          # Micron Technology, Inc.
    $ANALYZE_CMD "MA"          # Mastercard Incorporated
    $ANALYZE_CMD "COST"        # Costco Wholesale Corporation
    $ANALYZE_CMD "ORCL"        # Oracle Corporation
    $ANALYZE_CMD "ABBV"        # AbbVie Inc.
    $ANALYZE_CMD "NFLX"        # Netflix, Inc.
    $ANALYZE_CMD "PG"          # The Procter & Gamble Company
    $ANALYZE_CMD "HD"          # The Home Depot, Inc.
    $ANALYZE_CMD "CVX"         # Chevron Corporation
    $ANALYZE_CMD "GE"          # GE Aerospace
    $ANALYZE_CMD "BAC"         # Bank of America Corporation
    $ANALYZE_CMD "KO"          # The Coca-Cola Company
    $ANALYZE_CMD "CAT"         # Caterpillar Inc.
    $ANALYZE_CMD "BABA"        # Alibaba Group Holding Limited
    $ANALYZE_CMD "PLTR"        # Palantir Technologies Inc.
    $ANALYZE_CMD "AMD"         # Advanced Micro Devices, Inc.
    $ANALYZE_CMD "NVS"         # Novartis AG
    $ANALYZE_CMD "HSBC"        # HSBC Holdings plc
    $ANALYZE_CMD "TM"          # Toyota Motor Corporation
    $ANALYZE_CMD "CSCO"        # Cisco Systems, Inc.
    $ANALYZE_CMD "MRK"         # Merck & Co., Inc.
    $ANALYZE_CMD "AMAT"        # Applied Materials, Inc.
    $ANALYZE_CMD "LRCX"        # Lam Research Corporation
    $ANALYZE_CMD "PM"          # Philip Morris International Inc.
    $ANALYZE_CMD "RTX"         # RTX Corporation
    $ANALYZE_CMD "UNH"         # UnitedHealth Group Incorporated
    $ANALYZE_CMD "MS"          # Morgan Stanley
    $ANALYZE_CMD "GS"          # The Goldman Sachs Group, Inc.
    $ANALYZE_CMD "WFC"         # Wells Fargo & Company
    $ANALYZE_CMD "SAP"         # SAP SE
    $ANALYZE_CMD "SHEL"        # Shell plc
    $ANALYZE_CMD "MCD"         # McDonald's Corporation

    # ── 보유종목 ─────────────────────
    $ANALYZE_CMD  "DOW"         # Dow Inc
    $ANALYZE_CMD  "NNDM"        # Nano Dimension Ltd
    $ANALYZE_CMD  "INUV"        # Inuvo, Inc.
    $ANALYZE_CMD  "IONQ"        # IONQ Inc
    $ANALYZE_CMD  "MVIS"        # Microvision Inc
    $ANALYZE_CMD  "ARKG"        # ARK Genomic Revolution ETF
    $ANALYZE_CMD  "SPY"         # SPDR S&P 500 Trust ETF

    # ── 배당 보유종목 ─────────────────────
    $ANALYZE_CMD  "JEPI"        # JPMorgan Equity Premium Income ETF
    $ANALYZE_CMD  "AGNC"        # AGNC Investment Corp
    $ANALYZE_CMD  "KBWY"        # Invesco KBW Premium Yield Equity REIT ETF
    $ANALYZE_CMD  "RA"          # Brookfield Real Assets Income Fund Inc
    $ANALYZE_CMD  "QYLD"        # Global X NASDAQ 100 Covered Call ETF

    # ── 종목 검토 ─────────────────────
    $ANALYZE_CMD  "MRVL"        # Marvell Technology, Inc.
    echo "=== 미국 주식 분석 완료 ==="
}

# ── 옵션 처리 로직 ───────────────────────────
# $1은 스크립트 실행 시 전달되는 첫 번째 인자를 의미합니다.
case "$1" in
    ko)
        analyze_ko
        ;;
    us)
        analyze_us
        ;;
    all|"")
        analyze_ko
        echo "" # 줄바꿈
        analyze_us
        ;;
    *)
        # 잘못된 옵션을 입력했거나 옵션이 없는 경우 안내 메시지 출력
        echo "사용법: $0 {kor|us|all}"
        echo "  ko  : 한국 주식만 분석"
        echo "  us  : 미국 주식만 분석"
        echo "  all : 모든 주식 분석"
        exit 1
        ;;
esac