"""
설정 파일 로드 및 검증 모듈
"""

import os
import logging
import yaml

logger = logging.getLogger(__name__)


def load_yaml_config(file_path):
    """
    YAML 설정 파일 로드
    
    Args:
        file_path (str): 설정 파일 경로
        
    Returns:
        dict: 설정 데이터
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"설정 파일이 존재하지 않습니다: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            
        return config
    
    except Exception as e:
        logger.error(f"설정 파일 로드 중 오류 발생: {e}")
        return None


def validate_config(config):
    """
    설정 유효성 검사
    
    Args:
        config (dict): 설정 데이터
        
    Returns:
        bool: 유효성 검사 결과
    """
    # 필수 설정 항목 확인
    required_sections = ['trading', 'strategy', 'risk_management', 'logging']
    
    for section in required_sections:
        if section not in config:
            logger.error(f"필수 설정 항목이 누락되었습니다: {section}")
            return False
    
    # 거래 설정 검증
    if 'markets' not in config['trading'] or not config['trading']['markets']:
        logger.error("거래 마켓 설정이 누락되었습니다.")
        return False
    
    if 'interval' not in config['trading']:
        logger.warning("거래 간격이 지정되지 않았습니다. 기본값 5분을 사용합니다.")
        config['trading']['interval'] = 5
    
    # 전략 설정 검증
    strategy_indicators = ['ma_crossover', 'rsi', 'bollinger', 'volume']
    for indicator in strategy_indicators:
        if indicator not in config['strategy']:
            logger.warning(f"{indicator} 전략 설정이 누락되었습니다. 기본값을 사용합니다.")
            config['strategy'][indicator] = {'enabled': False}
    
    # 위험 관리 설정 검증
    risk_params = ['stop_loss', 'take_profit', 'trailing_stop', 'use_trailing_stop']
    for param in risk_params:
        if param not in config['risk_management']:
            logger.warning(f"{param} 위험 관리 설정이 누락되었습니다. 기본값을 사용합니다.")
            
            # 기본값 설정
            if param == 'stop_loss':
                config['risk_management'][param] = 0.03
            elif param == 'take_profit':
                config['risk_management'][param] = 0.05
            elif param == 'trailing_stop':
                config['risk_management'][param] = 0.02
            elif param == 'use_trailing_stop':
                config['risk_management'][param] = True
    
    return True


def load_api_keys(file_path):
    """
    API 키 설정 파일 로드
    
    Args:
        file_path (str): API 키 설정 파일 경로
        
    Returns:
        dict: API 키 설정 데이터
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"API 키 설정 파일이 존재하지 않습니다: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as file:
            api_keys = yaml.safe_load(file)
            
        # 필수 API 키 확인
        if 'upbit' not in api_keys:
            logger.error("업비트 API 키 설정이 누락되었습니다.")
            return None
        
        if 'access_key' not in api_keys['upbit'] or 'secret_key' not in api_keys['upbit']:
            logger.error("업비트 API 키 또는 시크릿 키가 누락되었습니다.")
            return None
        
        return api_keys
    
    except Exception as e:
        logger.error(f"API 키 설정 파일 로드 중 오류 발생: {e}")
        return None


def load_bot_config(config_path="config/config.yaml", api_keys_path="config/api_keys.yaml"):
    """
    봇 설정 및 API 키 로드
    
    Args:
        config_path (str): 설정 파일 경로
        api_keys_path (str): API 키 설정 파일 경로
        
    Returns:
        tuple: (봇 설정, API 키 설정)
    """
    # 설정 파일 로드
    config = load_yaml_config(config_path)
    if not config:
        return None, None
    
    # 설정 유효성 검사
    if not validate_config(config):
        return None, None
    
    # API 키 로드
    api_keys = load_api_keys(api_keys_path)
    
    return config, api_keys