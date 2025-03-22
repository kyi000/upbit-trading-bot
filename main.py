#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
업비트 자동 매매 봇 메인 실행 파일
"""

import os
import sys
import time
import signal
import argparse
import logging
from datetime import datetime

import schedule

from src.api.upbit_api import UpbitAPI
from src.strategies.combined_strategy import CombinedStrategy
from src.risk_management.risk_manager import RiskManager
from src.utils.config_loader import load_bot_config
from src.utils.logger import setup_logger
from src.utils.telegram_notifier import TelegramNotifier


# 전역 변수
running = True
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """
    시그널 핸들러
    """
    global running
    print("\n프로그램 종료 중...")
    running = False


def parse_arguments():
    """
    명령행 인자 파싱
    """
    parser = argparse.ArgumentParser(description='업비트 자동 매매 봇')
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='설정 파일 경로 (기본값: config/config.yaml)'
    )
    
    parser.add_argument(
        '--api-keys',
        type=str,
        default='config/api_keys.yaml',
        help='API 키 설정 파일 경로 (기본값: config/api_keys.yaml)'
    )
    
    return parser.parse_args()


def run_trading_cycle(api, strategy, risk_manager, notifier, config):
    """
    거래 사이클 실행
    """
    try:
        logger.info("거래 사이클 시작")
        
        # 시장 목록 가져오기
        markets = config['trading']['markets']
        
        # 거래 간격 가져오기
        interval = f"minute{config['trading']['interval']}"
        
        # 거래 사이클 실행
        cycle_result = strategy.run_trading_cycle(markets, interval)
        
        # 거래 결과 로깅
        for ticker, result in cycle_result['trades'].items():
            trade_result = result.get('trade_result', {})
            action = trade_result.get('action', 'hold')
            details = trade_result.get('details', "")
            
            if action != 'hold':
                logger.info(f"{ticker} - {action}: {details}")
                
                # 텔레그램 알림 전송
                notifier.notify_trade(action, ticker, details)
        
        # 위험 관리 확인
        risk_actions = risk_manager.check_risk_limits()
        
        # 위험 관리 조치 로깅 및 알림
        for ticker, action in risk_actions.get('actions', {}).items():
            if action['action'] != 'hold':
                logger.info(f"위험 관리 조치 - {ticker} - {action['action']}: {action['reason']}")
                
                # 텔레그램 알림 전송
                notifier.notify_risk_action(ticker, action)
        
        # 포트폴리오 정보 업데이트 (15분마다)
        current_minute = datetime.now().minute
        if current_minute % 15 == 0:
            portfolio_info = risk_manager.check_portfolio_risk()
            
            # 포트폴리오 정보 로깅
            logger.info(f"포트폴리오 상태 - 총 자산: {portfolio_info['total_balance']:,.0f} KRW, "
                       f"KRW 잔고: {portfolio_info['krw_balance']:,.0f} KRW, "
                       f"위험 수준: {portfolio_info['risk_level']}")
            
            # 텔레그램 알림 전송
            notifier.notify_portfolio(portfolio_info)
        
        logger.info("거래 사이클 종료")
        
    except Exception as e:
        logger.error(f"거래 사이클 실행 중 오류 발생: {e}")
        notifier.notify_error("거래 사이클", str(e))


def main():
    """
    메인 함수
    """
    # 인자 파싱
    args = parse_arguments()
    
    # 설정 로드
    config, api_keys = load_bot_config(args.config, args.api_keys)
    
    if not config or not api_keys:
        print("설정 로드 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    # 로거 설정
    logger = setup_logger(config)
    
    # 업비트 API 인스턴스 생성
    api = UpbitAPI(
        access_key=api_keys['upbit']['access_key'],
        secret_key=api_keys['upbit']['secret_key']
    )
    
    # 잔고 확인
    balance = api.get_balance("KRW")
    if balance is None:
        logger.error("API 키 인증 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    logger.info(f"API 연결 성공. 현재 잔고: {balance:,.0f} KRW")
    
    # 전략 인스턴스 생성
    strategy = CombinedStrategy(api, config)
    
    # 위험 관리 인스턴스 생성
    risk_manager = RiskManager(api, config)
    
    # 텔레그램 알림 인스턴스 생성
    notifier = TelegramNotifier.from_config({
        'notification': config['notification'],
        'api_keys': api_keys
    })
    
    # 시작 알림 전송
    notifier.notify_startup(version="1.0.0")
    
    # 현재 포트폴리오 상태 확인
    portfolio_info = risk_manager.check_portfolio_risk()
    logger.info(f"현재 포트폴리오 - 총 자산: {portfolio_info['total_balance']:,.0f} KRW")
    
    # 스케줄러 설정 (거래 간격에 따라)
    interval_minutes = config['trading']['interval']
    
    # 거래 사이클 스케줄링
    schedule.every(interval_minutes).minutes.do(
        run_trading_cycle, api, strategy, risk_manager, notifier, config
    )
    
    # 시작 직후 첫 거래 사이클 실행
    run_trading_cycle(api, strategy, risk_manager, notifier, config)
    
    logger.info(f"업비트 자동 매매 봇이 {interval_minutes}분 간격으로 동작 중입니다...")
    
    # 메인 루프
    while running:
        schedule.run_pending()
        time.sleep(1)
    
    logger.info("프로그램이 정상적으로 종료되었습니다.")


if __name__ == "__main__":
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 메인 함수 실행
    main()
