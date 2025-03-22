# 업비트 자동 매매 봇

복합 기술적 지표 기반 암호화폐 자동 거래 시스템

## 주요 기능

- 업비트 API를 활용한 실시간 시장 데이터 수집
- 다중 기술적 지표 기반 매매 신호 생성 (이동평균선, RSI, 볼린저 밴드)
- 설정 가능한 위험 관리 시스템 (손절매, 이익실현, 자산 배분)
- 백테스팅 시스템으로 전략 검증
- 텔레그램을 통한 알림 기능

## 프로젝트 구조

```
├── config/               # 설정 파일 디렉토리
│   ├── config.yaml      # 기본 설정 파일
│   └── api_keys.yaml    # API 키 설정 (gitignore에 포함됨)
├── src/                 # 소스 코드
│   ├── api/             # API 관련 모듈
│   ├── strategies/      # 거래 전략 모듈
│   ├── indicators/      # 기술적 지표 계산 모듈
│   ├── risk_management/ # 위험 관리 모듈
│   └── utils/           # 유틸리티 함수 모듈
├── tests/               # 테스트 코드
├── backtest/            # 백테스팅 모듈
├── data/                # 데이터 저장 디렉토리
├── logs/                # 로그 파일 디렉토리
├── main.py              # 메인 실행 파일
├── requirements.txt     # 필요 패키지 목록
└── setup.py             # 설치 스크립트
```

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/kyi000/upbit-trading-bot.git
cd upbit-trading-bot
```

2. 필요 패키지 설치
```bash
pip install -r requirements.txt
```

3. API 키 설정
```bash
cp config/api_keys.yaml.example config/api_keys.yaml
# config/api_keys.yaml 파일을 열고 업비트 API 키 정보 입력
```

4. 환경 설정
```bash
cp config/config.yaml.example config/config.yaml
# 필요에 따라 config/config.yaml 파일 수정
```

## 사용 방법

### 봇 실행
```bash
python main.py
```

### 백테스팅 실행
```bash
python backtest/run_backtest.py --config config/backtest_config.yaml
```

## 주의사항

- 이 봇은 투자 조언을 제공하지 않습니다.
- 가상화폐 투자에는 항상 위험이 따릅니다. 자기 책임 하에 사용하시기 바랍니다.
- 실제 자금을 투자하기 전에 충분한 백테스팅과 페이퍼 트레이딩을 권장합니다.

## 라이센스

MIT License