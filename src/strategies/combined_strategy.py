"""
복합 기술 지표 기반 거래 전략 모듈
"""

import logging
import time
from datetime import datetime

import pandas as pd
import numpy as np

from src.indicators.technical import TechnicalIndicators

logger = logging.getLogger(__name__)


class CombinedStrategy:
    """
    복합 기술 지표 기반 거래 전략 클래스
    """
    
    def __init__(self, api, config):
        """
        CombinedStrategy 클래스 초기화
        
        Args:
            api: UpbitAPI 인스턴스
            config (dict): 거래 전략 설정
        """
        self.api = api
        self.config = config
        self.positions = {}  # 보유 포지션 정보
        self.orders = {}  # 주문 정보
        self.last_signals = {}  # 마지막 신호
        
        logger.info("복합 거래 전략이 초기화되었습니다.")
    
    def update_market_data(self, ticker, interval='minute5', count=100):
        """
        시장 데이터 업데이트 및 지표 계산
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            interval (str): 캔들 간격
            count (int): 캔들 개수
            
        Returns:
            pd.DataFrame: 기술 지표가 계산된 데이터프레임
        """
        try:
            # 시장 데이터 조회
            df = self.api.get_ohlcv(ticker, interval=interval, count=count)
            
            if df is None or df.empty:
                logger.error(f"{ticker} 데이터 조회 실패")
                return None
            
            # 기술 지표 계산
            df = TechnicalIndicators.add_indicators(df, self.config['strategy'])
            
            # 최종 신호 계산
            df['signal'] = TechnicalIndicators.get_combined_signal(df)
            
            return df
            
        except Exception as e:
            logger.error(f"{ticker} 데이터 업데이트 중 오류 발생: {e}")
            return None
    
    def get_signal(self, ticker, interval='minute5', count=100):
        """
        현재 매매 신호 계산
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            interval (str): 캔들 간격
            count (int): 캔들 개수
            
        Returns:
            dict: 매매 신호 정보
                - signal: 신호 (1: 매수, -1: 매도, 0: 관망)
                - confidence: 신호 확신도 (0.0 ~ 1.0)
                - data: 데이터프레임
        """
        try:
            # 시장 데이터 업데이트
            df = self.update_market_data(ticker, interval, count)
            
            if df is None or df.empty:
                return {'signal': 0, 'confidence': 0.0, 'data': None}
            
            # 현재 신호
            current_signal = df['signal'].iloc[-1]
            
            # 신호 확신도 계산
            confidence = self._calculate_confidence(df)
            
            # 결과 반환
            result = {
                'signal': current_signal,
                'confidence': confidence,
                'data': df
            }
            
            # 마지막 신호 저장
            self.last_signals[ticker] = {
                'signal': current_signal,
                'confidence': confidence,
                'timestamp': datetime.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"{ticker} 신호 계산 중 오류 발생: {e}")
            return {'signal': 0, 'confidence': 0.0, 'data': None}
    
    def _calculate_confidence(self, df):
        """
        신호 확신도 계산
        
        Args:
            df (pd.DataFrame): 기술 지표가 계산된 데이터프레임
            
        Returns:
            float: 신호 확신도 (0.0 ~ 1.0)
        """
        # 확신도 계산 요소들 (각 요소는 0.0 ~ 1.0 사이 값)
        confidence_factors = []
        
        # 1. 일관된 신호 지속 기간
        signal = df['signal'].iloc[-1]
        consistent_signals = 0
        
        for i in range(2, 6):  # 최근 5개 캔들 확인
            if i <= len(df) and df['signal'].iloc[-i] == signal:
                consistent_signals += 1
                
        signal_consistency = consistent_signals / 4.0  # 0.0 ~ 1.0 정규화
        confidence_factors.append(signal_consistency)
        
        # 2. 이동평균선 교차 강도
        if 'ma_cross_signal' in df.columns and df['ma_cross_signal'].iloc[-1] != 0:
            # 단기선과 장기선의 차이 (상대적)
            ma_short = df.columns[df.columns.str.startswith('ma')].min()  # 가장 짧은 주기의 이평선
            ma_long = df.columns[df.columns.str.startswith('ma')].max()  # 가장 긴 주기의 이평선
            
            ma_diff = abs(df[ma_short].iloc[-1] - df[ma_long].iloc[-1]) / df['close'].iloc[-1]
            # 0.001 (0.1%) ~ 0.05 (5%) 정규화
            ma_cross_strength = min(1.0, max(0.0, (ma_diff - 0.001) / 0.049))
            confidence_factors.append(ma_cross_strength)
        
        # 3. 볼린저 밴드 상태
        if 'bb_bandwidth' in df.columns:
            # 변동성이 낮을수록 브레이크아웃 신호 확신도 높음
            # 볼린저 밴드폭 0.03 (3%) ~ 0.15 (15%) 정규화
            bb_confidence = 1.0 - min(1.0, max(0.0, (df['bb_bandwidth'].iloc[-1] - 0.03) / 0.12))
            confidence_factors.append(bb_confidence)
        
        # 4. RSI 값
        if 'rsi14' in df.columns:
            rsi = df['rsi14'].iloc[-1]
            if signal > 0:  # 매수 신호일 때
                # RSI가 30에 가까울수록 확신도 증가 (30 ~ 50 범위)
                rsi_confidence = 1.0 - min(1.0, max(0.0, (rsi - 30) / 20))
            elif signal < 0:  # 매도 신호일 때
                # RSI가 70에 가까울수록 확신도 증가 (50 ~ 70 범위)
                rsi_confidence = min(1.0, max(0.0, (rsi - 50) / 20))
            else:
                rsi_confidence = 0.5
            confidence_factors.append(rsi_confidence)
        
        # 5. 거래량 증가율
        if 'volume_ratio' in df.columns:
            # 거래량 비율 1.0 ~ 3.0 정규화
            volume_confidence = min(1.0, max(0.0, (df['volume_ratio'].iloc[-1] - 1.0) / 2.0))
            confidence_factors.append(volume_confidence)
        
        # 최종 확신도 계산 (모든 요소의 평균)
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # 기본값
    
    def execute_trade(self, ticker, signal_info):
        """
        매매 신호에 따라 거래 실행
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            signal_info (dict): 매매 신호 정보
                - signal: 신호 (1: 매수, -1: 매도, 0: 관망)
                - confidence: 신호 확신도 (0.0 ~ 1.0)
                - data: 데이터프레임
                
        Returns:
            dict: 거래 결과
                - success: 성공 여부
                - action: 수행된 작업 ("buy", "sell", "hold")
                - details: 추가 정보
        """
        try:
            signal = signal_info['signal']
            confidence = signal_info['confidence']
            
            # 신호 없음 또는 확신도가 낮으면 거래하지 않음
            if signal == 0 or confidence < 0.6:
                return {
                    'success': True,
                    'action': 'hold',
                    'details': f"신호 없음 또는 확신도 부족 (신호: {signal}, 확신도: {confidence:.2f})"
                }
            
            # 현재가 조회
            current_price = self.api.get_current_price(ticker)
            
            if current_price is None:
                return {
                    'success': False,
                    'action': 'hold',
                    'details': f"{ticker} 현재가 조회 실패"
                }
            
            # 계좌 잔고 확인
            krw_balance = self.api.get_balance("KRW")
            coin_balance = self.api.get_balance(ticker.split('-')[1])  # "KRW-BTC" -> "BTC"
            
            if krw_balance is None or coin_balance is None:
                return {
                    'success': False,
                    'action': 'hold',
                    'details': "잔고 조회 실패"
                }
            
            # 매수 신호
            if signal > 0:
                # 이미 충분히 보유하고 있으면 추가 매수하지 않음
                total_asset = krw_balance + (coin_balance * current_price)
                coin_ratio = (coin_balance * current_price) / total_asset
                
                if coin_ratio >= self.config['trading']['max_invest_ratio']:
                    return {
                        'success': True,
                        'action': 'hold',
                        'details': f"이미 충분히 보유 중 (비율: {coin_ratio:.2%})"
                    }
                
                # 매수할 금액 계산
                trade_amount = min(
                    self.config['trading']['trade_amount'],
                    krw_balance * 0.9,  # 수수료 고려하여 90%만 사용
                    (self.config['trading']['max_invest_ratio'] - coin_ratio) * total_asset
                )
                
                if trade_amount < 5000:  # 업비트 최소 주문 금액
                    return {
                        'success': True,
                        'action': 'hold',
                        'details': f"매수 금액이 최소 주문 금액보다 작음 ({trade_amount:.0f}원)"
                    }
                
                # 시장가 매수 주문
                order = self.api.buy_market_order(ticker, trade_amount)
                
                if order:
                    # 주문 정보 저장
                    self.orders[order['uuid']] = {
                        'ticker': ticker,
                        'type': 'buy',
                        'price': current_price,
                        'amount': trade_amount,
                        'timestamp': datetime.now()
                    }
                    
                    return {
                        'success': True,
                        'action': 'buy',
                        'details': {
                            'order_id': order['uuid'],
                            'amount': trade_amount,
                            'price': current_price
                        }
                    }
                else:
                    return {
                        'success': False,
                        'action': 'hold',
                        'details': "매수 주문 실패"
                    }
            
            # 매도 신호
            elif signal < 0:
                # 보유하고 있지 않으면 매도하지 않음
                if coin_balance <= 0:
                    return {
                        'success': True,
                        'action': 'hold',
                        'details': "보유 수량 없음"
                    }
                
                # 매도할 수량 계산 (전량 매도)
                trade_volume = coin_balance
                
                # 시장가 매도 주문
                order = self.api.sell_market_order(ticker, trade_volume)
                
                if order:
                    # 주문 정보 저장
                    self.orders[order['uuid']] = {
                        'ticker': ticker,
                        'type': 'sell',
                        'price': current_price,
                        'volume': trade_volume,
                        'timestamp': datetime.now()
                    }
                    
                    return {
                        'success': True,
                        'action': 'sell',
                        'details': {
                            'order_id': order['uuid'],
                            'volume': trade_volume,
                            'price': current_price
                        }
                    }
                else:
                    return {
                        'success': False,
                        'action': 'hold',
                        'details': "매도 주문 실패"
                    }
            
            # 관망
            else:
                return {
                    'success': True,
                    'action': 'hold',
                    'details': "관망 신호"
                }
                
        except Exception as e:
            logger.error(f"{ticker} 거래 실행 중 오류 발생: {e}")
            return {
                'success': False,
                'action': 'hold',
                'details': f"오류: {str(e)}"
            }
    
    def run_trading_cycle(self, markets, interval='minute5'):
        """
        지정된 마켓들에 대해 하나의 거래 사이클 실행
        
        Args:
            markets (list): 거래할 마켓(티커) 목록
            interval (str): 캔들 간격
            
        Returns:
            dict: 거래 사이클 결과
                - trades: 각 마켓별 거래 결과
                - timestamp: 실행 시간
        """
        results = {}
        
        for ticker in markets:
            try:
                # 매매 신호 계산
                signal_info = self.get_signal(ticker, interval)
                
                # 거래 실행
                trade_result = self.execute_trade(ticker, signal_info)
                
                # 결과 저장
                results[ticker] = {
                    'signal': signal_info['signal'],
                    'confidence': signal_info['confidence'],
                    'trade_result': trade_result
                }
                
                # API 호출 제한을 위한 간격 조절
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"{ticker} 거래 사이클 중 오류 발생: {e}")
                results[ticker] = {
                    'signal': 0,
                    'confidence': 0.0,
                    'trade_result': {
                        'success': False,
                        'action': 'hold',
                        'details': f"오류: {str(e)}"
                    }
                }
        
        return {
            'trades': results,
            'timestamp': datetime.now()
        }
