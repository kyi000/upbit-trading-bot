"""
로깅 설정 모듈
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import time


def setup_logger(config):
    """
    로거 설정
    
    Args:
        config (dict): 로깅 설정
            - level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            - file: 로그 파일 경로
            - max_size: 최대 로그 파일 크기
            - backup_count: 백업 파일 수
            
    Returns:
        logging.Logger: 설정된 로거
    """
    # 로깅 디렉토리 생성
    log_file = config['logging']['file']
    log_dir = os.path.dirname(log_file)
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로깅 레벨 설정
    level_str = config['logging'].get('level', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)
    
    # 로깅 포맷 설정
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 기본 로거 설정
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format
    )
    
    # 루트 로거 가져오기
    logger = logging.getLogger()
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    # 파일 핸들러 추가
    max_size = config['logging'].get('max_size', 10 * 1024 * 1024)  # 기본값 10MB
    backup_count = config['logging'].get('backup_count', 10)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)
    
    # 로거 반환
    return logger


def log_trade(logger, action, ticker, details):
    """
    거래 로깅
    
    Args:
        logger: 로거 인스턴스
        action (str): 거래 유형 (buy, sell, hold)
        ticker (str): 티커
        details (dict): 거래 세부 정보
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    action_str = {
        'buy': '매수',
        'sell': '매도',
        'hold': '관망'
    }.get(action, action)
    
    message = f"[{timestamp}] {action_str} - {ticker} - "
    
    if isinstance(details, dict):
        details_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
        message += details_str
    else:
        message += str(details)
    
    if action == 'buy':
        logger.info(message)
    elif action == 'sell':
        logger.info(message)
    else:
        logger.debug(message)


def log_portfolio(logger, portfolio_info):
    """
    포트폴리오 상태 로깅
    
    Args:
        logger: 로거 인스턴스
        portfolio_info (dict): 포트폴리오 정보
            - total_balance: 총 자산 가치
            - krw_balance: KRW 잔고
            - portfolio_exposure: 코인별 포트폴리오 노출도
            - risk_level: 위험 수준
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    total_balance = portfolio_info.get('total_balance', 0)
    krw_balance = portfolio_info.get('krw_balance', 0)
    risk_level = portfolio_info.get('risk_level', 'unknown')
    
    message = f"[{timestamp}] 포트폴리오 상태 - "
    message += f"총 자산: {total_balance:,.0f} KRW, "
    message += f"KRW 잔고: {krw_balance:,.0f} KRW, "
    message += f"위험 수준: {risk_level}"
    
    logger.info(message)
    
    # 코인별 상세 정보 로깅
    exposure = portfolio_info.get('portfolio_exposure', {})
    
    for ticker, info in exposure.items():
        coin_message = f"[{timestamp}] 보유 코인 - {ticker} - "
        coin_message += f"수량: {info.get('quantity', 0):.8f}, "
        coin_message += f"가치: {info.get('value', 0):,.0f} KRW, "
        coin_message += f"비중: {info.get('ratio', 0):.2%}"
        
        logger.info(coin_message)


def log_error(logger, module, error_msg):
    """
    오류 로깅
    
    Args:
        logger: 로거 인스턴스
        module (str): 오류 발생 모듈
        error_msg (str): 오류 메시지
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    message = f"[{timestamp}] 오류 - {module} - {error_msg}"
    
    logger.error(message)
