"""
업비트 API를 사용하기 위한 인터페이스 모듈
"""

import logging
import time
from datetime import datetime

import pandas as pd
import pyupbit
from pyupbit.request_api import _call_public_api

logger = logging.getLogger(__name__)


class UpbitAPI:
    """
    업비트 API 인터페이스 클래스
    """

    def __init__(self, access_key=None, secret_key=None):
        """
        UpbitAPI 클래스 초기화
        
        Args:
            access_key (str, optional): 업비트 API 접근 키
            secret_key (str, optional): 업비트 API 비밀 키
        """
        self.access_key = access_key
        self.secret_key = secret_key
        
        # API 키가 제공된 경우 인증 객체 생성
        if access_key and secret_key:
            self.upbit = pyupbit.Upbit(access_key, secret_key)
            logger.info("업비트 API 인증 성공")
        else:
            self.upbit = None
            logger.warning("업비트 API 키가 제공되지 않아 인증되지 않은 상태로 실행됩니다.")
    
    def get_current_price(self, ticker):
        """
        현재가 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            
        Returns:
            float: 현재가
        """
        try:
            price = pyupbit.get_current_price(ticker)
            return price
        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            return None
    
    def get_ohlcv(self, ticker, interval="day", count=200, to=None):
        """
        캔들 데이터 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            interval (str, optional): 시간 간격. Defaults to "day".
                - 1분: "minute1"
                - 3분: "minute3"
                - 5분: "minute5"
                - 15분: "minute15"
                - 30분: "minute30"
                - 60분: "minute60"
                - 일봉: "day"
                - 주봉: "week"
                - 월봉: "month"
            count (int, optional): 캔들 개수. Defaults to 200.
            to (str, optional): 마지막 캔들의 시간. Defaults to None.
                - 포맷: yyyy-MM-dd HH:mm:ss
            
        Returns:
            pd.DataFrame: OHLCV 데이터프레임
        """
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=count, to=to)
            return df
        except Exception as e:
            logger.error(f"OHLCV 조회 실패: {e}")
            return None
    
    def get_orderbook(self, ticker):
        """
        호가창 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            
        Returns:
            dict: 호가창 정보
        """
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            return orderbook
        except Exception as e:
            logger.error(f"호가창 조회 실패: {e}")
            return None
    
    def get_daily_candle(self, ticker, count=200):
        """
        일봉 데이터 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            count (int, optional): 캔들 개수. Defaults to 200.
            
        Returns:
            pd.DataFrame: 일봉 데이터
        """
        return self.get_ohlcv(ticker, interval="day", count=count)
    
    def get_minute_candle(self, ticker, unit=1, count=200):
        """
        분봉 데이터 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            unit (int, optional): 분 단위 (1, 3, 5, 15, 30, 60). Defaults to 1.
            count (int, optional): 캔들 개수. Defaults to 200.
            
        Returns:
            pd.DataFrame: 분봉 데이터
        """
        interval = f"minute{unit}"
        return self.get_ohlcv(ticker, interval=interval, count=count)
    
    def get_balance(self, ticker=None):
        """
        보유 자산 조회
        
        Args:
            ticker (str, optional): 티커. Defaults to None.
                - None인 경우 모든 자산 조회
                - "KRW"인 경우 원화 잔고 조회
                - "BTC"인 경우 비트코인 잔고 조회
                
        Returns:
            float or dict: 보유 자산 정보
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 잔고 조회 시도")
            return None
            
        try:
            if ticker:
                return self.upbit.get_balance(ticker)
            else:
                return self.upbit.get_balances()
        except Exception as e:
            logger.error(f"보유 자산 조회 실패: {e}")
            return None
    
    def buy_limit_order(self, ticker, price, volume):
        """
        지정가 매수
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            price (float): 주문 가격
            volume (float): 주문 수량
            
        Returns:
            dict: 주문 결과
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 매수 주문 시도")
            return None
            
        try:
            return self.upbit.buy_limit_order(ticker, price, volume)
        except Exception as e:
            logger.error(f"지정가 매수 주문 실패: {e}")
            return None
    
    def sell_limit_order(self, ticker, price, volume):
        """
        지정가 매도
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            price (float): 주문 가격
            volume (float): 주문 수량
            
        Returns:
            dict: 주문 결과
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 매도 주문 시도")
            return None
            
        try:
            return self.upbit.sell_limit_order(ticker, price, volume)
        except Exception as e:
            logger.error(f"지정가 매도 주문 실패: {e}")
            return None
    
    def buy_market_order(self, ticker, price):
        """
        시장가 매수
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            price (float): 주문 금액
            
        Returns:
            dict: 주문 결과
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 매수 주문 시도")
            return None
            
        try:
            return self.upbit.buy_market_order(ticker, price)
        except Exception as e:
            logger.error(f"시장가 매수 주문 실패: {e}")
            return None
    
    def sell_market_order(self, ticker, volume):
        """
        시장가 매도
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            volume (float): 주문 수량
            
        Returns:
            dict: 주문 결과
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 매도 주문 시도")
            return None
            
        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            logger.error(f"시장가 매도 주문 실패: {e}")
            return None
    
    def get_order(self, uuid):
        """
        주문 조회
        
        Args:
            uuid (str): 주문 UUID
            
        Returns:
            dict: 주문 정보
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 주문 조회 시도")
            return None
            
        try:
            return self.upbit.get_order(uuid)
        except Exception as e:
            logger.error(f"주문 조회 실패: {e}")
            return None
    
    def cancel_order(self, uuid):
        """
        주문 취소
        
        Args:
            uuid (str): 주문 UUID
            
        Returns:
            dict: 취소 결과
        """
        if not self.upbit:
            logger.error("인증되지 않은 상태에서 주문 취소 시도")
            return None
            
        try:
            return self.upbit.cancel_order(uuid)
        except Exception as e:
            logger.error(f"주문 취소 실패: {e}")
            return None
    
    def get_transaction_history(self, ticker, to=None, count=100):
        """
        체결 내역 조회
        
        Args:
            ticker (str): 티커 (예: "KRW-BTC")
            to (str, optional): 마지막 체결 시간. Defaults to None.
            count (int, optional): 체결 개수. Defaults to 100.
            
        Returns:
            list: 체결 내역
        """
        try:
            url = "trades/ticks"
            params = {"market": ticker, "count": count}
            if to:
                params["to"] = to
                
            return _call_public_api(url, params=params)
        except Exception as e:
            logger.error(f"체결 내역 조회 실패: {e}")
            return None
    
    def get_tickers(self, fiat="KRW"):
        """
        티커 목록 조회
        
        Args:
            fiat (str, optional): 기준 화폐. Defaults to "KRW".
                - "KRW": 원화 마켓
                - "BTC": BTC 마켓
                - "USDT": USDT 마켓
                - None: 모든 마켓
                
        Returns:
            list: 티커 목록
        """
        try:
            tickers = pyupbit.get_tickers(fiat=fiat)
            return tickers
        except Exception as e:
            logger.error(f"티커 목록 조회 실패: {e}")
            return None