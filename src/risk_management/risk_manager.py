"""
위험 관리 모듈
"""

import logging
import time
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class RiskManager:
    """
    위험 관리 클래스
    """
    
    def __init__(self, api, config):
        """
        RiskManager 클래스 초기화
        
        Args:
            api: UpbitAPI 인스턴스
            config (dict): 위험 관리 설정
        """
        self.api = api
        self.config = config
        self.positions = {}  # 포지션 관리 (ticker: {entry_price, entry_time, quantity, trailing_stop_price})
        
        logger.info("위험 관리자가 초기화되었습니다.")
    
    def update_positions(self):
        """
        현재 보유 중인 포지션 정보 업데이트
        
        Returns:
            dict: 업데이트된 포지션 정보
        """
        try:
            # 보유 자산 조회
            balances = self.api.get_balance()
            
            if not balances:
                logger.error("잔고 조회 실패")
                return self.positions
            
            # 기존 포지션 정보 저장
            old_positions = self.positions.copy()
            
            # 포지션 업데이트
            new_positions = {}
            
            for balance in balances:
                currency = balance['currency']
                
                # KRW는 제외
                if currency == 'KRW':
                    continue
                
                # 잔고가 없으면 건너뛰기
                if float(balance['balance']) <= 0:
                    continue
                
                # 티커 생성 ("KRW-BTC" 형식)
                ticker = f"KRW-{currency}"
                
                # 현재가 조회
                current_price = self.api.get_current_price(ticker)
                
                if not current_price:
                    logger.error(f"{ticker} 현재가 조회 실패")
                    continue
                
                # 포지션 정보 생성/업데이트
                if ticker in old_positions:
                    # 기존 포지션 업데이트
                    new_positions[ticker] = old_positions[ticker].copy()
                    new_positions[ticker]['quantity'] = float(balance['balance'])
                    new_positions[ticker]['current_price'] = current_price
                    
                    # 평균 매수가가 없으면 현재가로 설정
                    if 'entry_price' not in new_positions[ticker]:
                        new_positions[ticker]['entry_price'] = current_price
                        
                    # 최고가 추적 (이익실현 계산용)
                    if 'highest_price' not in new_positions[ticker] or current_price > new_positions[ticker]['highest_price']:
                        new_positions[ticker]['highest_price'] = current_price
                        
                    # 최저가 추적 (손절매 계산용)
                    if 'lowest_price' not in new_positions[ticker] or current_price < new_positions[ticker]['lowest_price']:
                        new_positions[ticker]['lowest_price'] = current_price
                    
                    # 트레일링 스탑 가격 업데이트
                    if self.config['risk_management']['use_trailing_stop']:
                        self._update_trailing_stop(new_positions[ticker], current_price)
                else:
                    # 새로운 포지션 생성
                    new_positions[ticker] = {
                        'currency': currency,
                        'quantity': float(balance['balance']),
                        'entry_price': current_price,  # 현재가를 매수가로 가정
                        'entry_time': datetime.now(),
                        'current_price': current_price,
                        'highest_price': current_price,
                        'lowest_price': current_price
                    }
                    
                    # 트레일링 스탑 초기화
                    if self.config['risk_management']['use_trailing_stop']:
                        trailing_stop_price = current_price * (1 - self.config['risk_management']['trailing_stop'])
                        new_positions[ticker]['trailing_stop_price'] = trailing_stop_price
            
            # 포지션 정보 갱신
            self.positions = new_positions
            
            return self.positions
            
        except Exception as e:
            logger.error(f"포지션 업데이트 중 오류 발생: {e}")
            return self.positions
    
    def _update_trailing_stop(self, position, current_price):
        """
        트레일링 스탑 가격 업데이트
        
        Args:
            position (dict): 포지션 정보
            current_price (float): 현재가
        """
        # 트레일링 스탑 가격이 없으면 초기화
        if 'trailing_stop_price' not in position:
            trailing_stop_price = current_price * (1 - self.config['risk_management']['trailing_stop'])
            position['trailing_stop_price'] = trailing_stop_price
            return
        
        # 현재가가 상승했을 때만 트레일링 스탑 가격 업데이트
        new_stop_price = current_price * (1 - self.config['risk_management']['trailing_stop'])
        
        if new_stop_price > position['trailing_stop_price']:
            position['trailing_stop_price'] = new_stop_price
    
    def check_risk_limits(self):
        """
        모든 포지션에 대해 위험 한도 확인 및 필요 시 주문 실행
        
        Returns:
            dict: 위험 관리 조치 결과
                - actions: 각 티커별 조치 결과
                - timestamp: 실행 시간
        """
        try:
            # 포지션 업데이트
            self.update_positions()
            
            actions = {}
            
            for ticker, position in self.positions.items():
                # 위험 관리 조치 확인
                risk_action = self._check_position_risk(ticker, position)
                
                if risk_action['action'] != 'hold':
                    # 필요한 조치 실행
                    execution_result = self._execute_risk_action(ticker, position, risk_action)
                    actions[ticker] = execution_result
                else:
                    actions[ticker] = risk_action
            
            return {
                'actions': actions,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"위험 한도 확인 중 오류 발생: {e}")
            return {
                'actions': {},
                'timestamp': datetime.now()
            }
    
    def _check_position_risk(self, ticker, position):
        """
        단일 포지션의 위험 관리 조치 확인
        
        Args:
            ticker (str): 티커
            position (dict): 포지션 정보
            
        Returns:
            dict: 위험 관리 조치 정보
                - action: 조치 ("sell", "partial_sell", "hold")
                - reason: 조치 이유
                - details: 세부 정보
        """
        # 현재 수익률 계산
        current_price = position['current_price']
        entry_price = position['entry_price']
        profit_pct = (current_price - entry_price) / entry_price
        
        # 1. 손절매 확인
        stop_loss = self.config['risk_management']['stop_loss']
        
        if profit_pct <= -stop_loss:
            return {
                'action': 'sell',
                'reason': 'stop_loss',
                'details': {
                    'profit_pct': profit_pct,
                    'threshold': -stop_loss,
                    'entry_price': entry_price,
                    'current_price': current_price
                }
            }
        
        # 2. 트레일링 스탑 확인
        if self.config['risk_management']['use_trailing_stop'] and 'trailing_stop_price' in position:
            if current_price <= position['trailing_stop_price']:
                return {
                    'action': 'sell',
                    'reason': 'trailing_stop',
                    'details': {
                        'trailing_stop_price': position['trailing_stop_price'],
                        'current_price': current_price,
                        'highest_price': position['highest_price']
                    }
                }
        
        # 3. 이익실현 확인
        take_profit = self.config['risk_management']['take_profit']
        
        if profit_pct >= take_profit:
            return {
                'action': 'partial_sell',
                'reason': 'take_profit',
                'details': {
                    'profit_pct': profit_pct,
                    'threshold': take_profit,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'sell_ratio': 0.5  # 보유량의 50% 매도
                }
            }
        
        # 조치 불필요
        return {
            'action': 'hold',
            'reason': 'within_limits',
            'details': {
                'profit_pct': profit_pct,
                'entry_price': entry_price,
                'current_price': current_price
            }
        }
    
    def _execute_risk_action(self, ticker, position, risk_action):
        """
        위험 관리 조치 실행
        
        Args:
            ticker (str): 티커
            position (dict): 포지션 정보
            risk_action (dict): 위험 관리 조치 정보
            
        Returns:
            dict: 실행 결과
                - success: 성공 여부
                - action: 실행된 조치
                - reason: 조치 이유
                - details: 세부 정보
        """
        try:
            action = risk_action['action']
            reason = risk_action['reason']
            
            if action == 'sell':
                # 전량 매도
                volume = position['quantity']
                order = self.api.sell_market_order(ticker, volume)
                
                if order:
                    # 포지션에서 제거
                    if ticker in self.positions:
                        del self.positions[ticker]
                    
                    return {
                        'success': True,
                        'action': 'sell',
                        'reason': reason,
                        'details': {
                            'order_id': order['uuid'],
                            'volume': volume,
                            'price': position['current_price']
                        }
                    }
                else:
                    return {
                        'success': False,
                        'action': 'hold',
                        'reason': reason,
                        'details': "매도 주문 실패"
                    }
                    
            elif action == 'partial_sell':
                # 부분 매도 (기본값: 보유량의 50%)
                sell_ratio = risk_action['details'].get('sell_ratio', 0.5)
                volume = position['quantity'] * sell_ratio
                
                order = self.api.sell_market_order(ticker, volume)
                
                if order:
                    # 포지션 업데이트
                    position['quantity'] -= volume
                    
                    return {
                        'success': True,
                        'action': 'partial_sell',
                        'reason': reason,
                        'details': {
                            'order_id': order['uuid'],
                            'volume': volume,
                            'price': position['current_price'],
                            'remaining': position['quantity']
                        }
                    }
                else:
                    return {
                        'success': False,
                        'action': 'hold',
                        'reason': reason,
                        'details': "부분 매도 주문 실패"
                    }
            else:
                return {
                    'success': True,
                    'action': 'hold',
                    'reason': reason,
                    'details': risk_action['details']
                }
                
        except Exception as e:
            logger.error(f"{ticker} 위험 관리 조치 실행 중 오류 발생: {e}")
            return {
                'success': False,
                'action': 'hold',
                'reason': risk_action['reason'],
                'details': f"오류: {str(e)}"
            }
    
    def check_portfolio_risk(self):
        """
        포트폴리오 전체 위험 확인
        
        Returns:
            dict: 포트폴리오 위험 정보
                - total_balance: 총 자산 가치 (KRW)
                - portfolio_exposure: 코인별 포트폴리오 노출도
                - risk_level: 위험 수준 (low, medium, high)
        """
        try:
            # 보유 자산 조회
            krw_balance = self.api.get_balance("KRW") or 0
            balances = self.api.get_balance() or []
            
            # 총 자산 가치 계산
            total_value = float(krw_balance)
            portfolio_exposure = {}
            
            for balance in balances:
                currency = balance['currency']
                
                # KRW는 이미 계산됨
                if currency == 'KRW':
                    continue
                
                # 잔고가 없으면 건너뛰기
                if float(balance['balance']) <= 0:
                    continue
                
                # 티커 생성 ("KRW-BTC" 형식)
                ticker = f"KRW-{currency}"
                
                # 현재가 조회
                current_price = self.api.get_current_price(ticker)
                
                if not current_price:
                    logger.error(f"{ticker} 현재가 조회 실패")
                    continue
                
                # 코인별 가치 계산
                coin_value = float(balance['balance']) * current_price
                total_value += coin_value
                
                # 포트폴리오 노출도 계산
                portfolio_exposure[ticker] = {
                    'value': coin_value,
                    'quantity': float(balance['balance']),
                    'price': current_price
                }
            
            # 각 코인의 포트폴리오 비중 계산
            for ticker in portfolio_exposure:
                portfolio_exposure[ticker]['ratio'] = portfolio_exposure[ticker]['value'] / total_value if total_value > 0 else 0
            
            # 위험 수준 결정
            risk_level = "low"
            max_exposure = max([exposure.get('ratio', 0) for exposure in portfolio_exposure.values()], default=0)
            
            if max_exposure > 0.5:  # 단일 코인이 50% 이상을 차지하면 high risk
                risk_level = "high"
            elif max_exposure > 0.3:  # 단일 코인이 30% 이상을 차지하면 medium risk
                risk_level = "medium"
            
            return {
                'total_balance': total_value,
                'krw_balance': krw_balance,
                'portfolio_exposure': portfolio_exposure,
                'risk_level': risk_level,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"포트폴리오 위험 확인 중 오류 발생: {e}")
            return {
                'total_balance': 0,
                'krw_balance': 0,
                'portfolio_exposure': {},
                'risk_level': 'unknown',
                'timestamp': datetime.now()
            }
    
    def rebalance_portfolio(self, target_allocations):
        """
        포트폴리오 리밸런싱
        
        Args:
            target_allocations (dict): 목표 자산 배분 비율 (ticker: ratio)
                예: {"KRW-BTC": 0.3, "KRW-ETH": 0.2, "KRW": 0.5}
                
        Returns:
            dict: 리밸런싱 결과
                - success: 성공 여부
                - actions: 수행된 조치들
                - details: 세부 정보
        """
        try:
            # 현재 포트폴리오 상태 확인
            portfolio = self.check_portfolio_risk()
            
            if not portfolio or portfolio['total_balance'] <= 0:
                return {
                    'success': False,
                    'actions': [],
                    'details': "포트폴리오 정보 조회 실패"
                }
            
            total_balance = portfolio['total_balance']
            krw_balance = portfolio['krw_balance']
            portfolio_exposure = portfolio['portfolio_exposure']
            
            actions = []
            
            # 1. 매도가 필요한 코인 처리
            for ticker, exposure in portfolio_exposure.items():
                current_ratio = exposure['ratio']
                target_ratio = target_allocations.get(ticker, 0)
                
                if current_ratio > target_ratio:
                    # 초과분 매도
                    excess_value = (current_ratio - target_ratio) * total_balance
                    sell_quantity = excess_value / exposure['price']
                    
                    # 수량 보정 (소수점 자리수 등)
                    sell_quantity = min(sell_quantity, exposure['quantity'])
                    
                    if sell_quantity > 0:
                        # 매도 주문
                        order = self.api.sell_market_order(ticker, sell_quantity)
                        
                        if order:
                            actions.append({
                                'action': 'sell',
                                'ticker': ticker,
                                'quantity': sell_quantity,
                                'value': sell_quantity * exposure['price'],
                                'order_id': order['uuid']
                            })
                        else:
                            return {
                                'success': False,
                                'actions': actions,
                                'details': f"{ticker} 매도 주문 실패"
                            }
            
            # API 호출 제한을 위한 지연
            time.sleep(1)
            
            # 2. 업데이트된 KRW 잔고 확인
            krw_balance = self.api.get_balance("KRW") or 0
            
            # 3. 매수가 필요한 코인 처리
            for ticker, target_ratio in target_allocations.items():
                # KRW는 별도 처리
                if ticker == 'KRW':
                    continue
                
                current_ratio = portfolio_exposure.get(ticker, {}).get('ratio', 0)
                
                if current_ratio < target_ratio:
                    # 부족분 매수
                    deficit_value = (target_ratio - current_ratio) * total_balance
                    
                    # KRW 잔고 확인
                    if deficit_value > krw_balance:
                        deficit_value = krw_balance
                    
                    if deficit_value >= 5000:  # 업비트 최소 주문 금액
                        # 매수 주문
                        order = self.api.buy_market_order(ticker, deficit_value)
                        
                        if order:
                            actions.append({
                                'action': 'buy',
                                'ticker': ticker,
                                'value': deficit_value,
                                'order_id': order['uuid']
                            })
                            
                            # 사용한 KRW 차감
                            krw_balance -= deficit_value
                        else:
                            return {
                                'success': False,
                                'actions': actions,
                                'details': f"{ticker} 매수 주문 실패"
                            }
            
            return {
                'success': True,
                'actions': actions,
                'details': "포트폴리오 리밸런싱 완료",
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"포트폴리오 리밸런싱 중 오류 발생: {e}")
            return {
                'success': False,
                'actions': [],
                'details': f"오류: {str(e)}",
                'timestamp': datetime.now()
            }
