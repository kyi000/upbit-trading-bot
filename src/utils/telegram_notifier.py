"""
텔레그램 알림 모듈
"""

import logging
import asyncio
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    텔레그램 알림 클래스
    """
    
    def __init__(self, token=None, chat_id=None, enabled=False):
        """
        TelegramNotifier 클래스 초기화
        
        Args:
            token (str): 텔레그램 봇 토큰
            chat_id (str): 텔레그램 채팅 ID
            enabled (bool): 알림 활성화 여부
        """
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled and token and chat_id
        self.bot = Bot(token=token) if self.enabled else None
        
        if self.enabled:
            logger.info("텔레그램 알림이 활성화되었습니다.")
        else:
            logger.info("텔레그램 알림이 비활성화되었습니다.")
    
    @staticmethod
    def from_config(config):
        """
        설정에서 텔레그램 알림 인스턴스 생성
        
        Args:
            config (dict): 설정 데이터
            
        Returns:
            TelegramNotifier: 텔레그램 알림 인스턴스
        """
        try:
            # 텔레그램 알림 설정 확인
            telegram_enabled = config.get('notification', {}).get('telegram', {}).get('enabled', False)
            
            if not telegram_enabled:
                return TelegramNotifier(enabled=False)
            
            # API 키 확인
            api_keys = config.get('api_keys', {})
            
            if not api_keys or 'telegram' not in api_keys:
                logger.warning("텔레그램 API 키가 설정되지 않았습니다.")
                return TelegramNotifier(enabled=False)
            
            token = api_keys['telegram'].get('token')
            chat_id = api_keys['telegram'].get('chat_id')
            
            if not token or not chat_id:
                logger.warning("텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다.")
                return TelegramNotifier(enabled=False)
            
            return TelegramNotifier(token=token, chat_id=chat_id, enabled=True)
            
        except Exception as e:
            logger.error(f"텔레그램 알림 초기화 중 오류 발생: {e}")
            return TelegramNotifier(enabled=False)
    
    async def send_message_async(self, message):
        """
        텔레그램 메시지 비동기 전송
        
        Args:
            message (str): 전송할 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
            return True
            
        except TelegramError as e:
            logger.error(f"텔레그램 메시지 전송 중 오류 발생: {e}")
            return False
    
    def send_message(self, message):
        """
        텔레그램 메시지 동기 전송
        
        Args:
            message (str): 전송할 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.send_message_async(message))
            loop.close()
            return result
            
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 중 오류 발생: {e}")
            return False
    
    def notify_trade(self, action, ticker, details):
        """
        거래 알림 전송
        
        Args:
            action (str): 거래 유형 (buy, sell, hold)
            ticker (str): 티커
            details (dict): 거래 세부 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        action_str = {
            'buy': '매수',
            'sell': '매도',
            'hold': '관망'
        }.get(action, action)
        
        # 메시지 생성
        message = f"<b>[{action_str}] {ticker}</b> ({timestamp})\n\n"
        
        if isinstance(details, dict):
            # 가격 정보
            if 'price' in details:
                message += f"가격: {details['price']:,.0f} KRW\n"
            
            # 수량 정보
            if 'volume' in details:
                message += f"수량: {details['volume']:.8f}\n"
            elif 'amount' in details:
                message += f"금액: {details['amount']:,.0f} KRW\n"
            
            # 주문 ID
            if 'order_id' in details:
                message += f"주문 ID: {details['order_id']}\n"
        else:
            message += str(details)
        
        return self.send_message(message)
    
    def notify_risk_action(self, ticker, action_info):
        """
        위험 관리 조치 알림 전송
        
        Args:
            ticker (str): 티커
            action_info (dict): 위험 관리 조치 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        action = action_info.get('action', 'unknown')
        reason = action_info.get('reason', 'unknown')
        details = action_info.get('details', {})
        
        # 관망은 알림 제외
        if action == 'hold':
            return False
        
        # 액션 문자열 변환
        action_str = {
            'sell': '매도',
            'partial_sell': '일부 매도',
            'unknown': '알 수 없음'
        }.get(action, action)
        
        # 이유 문자열 변환
        reason_str = {
            'stop_loss': '손절매',
            'trailing_stop': '추적 손절매',
            'take_profit': '이익실현',
            'unknown': '알 수 없음'
        }.get(reason, reason)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 메시지 생성
        message = f"<b>[위험관리] {action_str} - {ticker}</b> ({timestamp})\n"
        message += f"원인: {reason_str}\n\n"
        
        if isinstance(details, dict):
            # 수익률 정보
            if 'profit_pct' in details:
                message += f"수익률: {details['profit_pct']:.2%}\n"
            
            # 가격 정보
            if 'entry_price' in details and 'current_price' in details:
                message += f"매수가: {details['entry_price']:,.0f} KRW\n"
                message += f"현재가: {details['current_price']:,.0f} KRW\n"
            
            # 매도 정보
            if 'volume' in details:
                message += f"매도 수량: {details['volume']:.8f}\n"
            
            # 추적 손절매 정보
            if 'trailing_stop_price' in details:
                message += f"추적 손절매 가격: {details['trailing_stop_price']:,.0f} KRW\n"
        
        return self.send_message(message)
    
    def notify_portfolio(self, portfolio_info):
        """
        포트폴리오 상태 알림 전송
        
        Args:
            portfolio_info (dict): 포트폴리오 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        total_balance = portfolio_info.get('total_balance', 0)
        krw_balance = portfolio_info.get('krw_balance', 0)
        risk_level = portfolio_info.get('risk_level', 'unknown')
        
        # 메시지 생성
        message = f"<b>[포트폴리오 상태]</b> ({timestamp})\n\n"
        message += f"총 자산: {total_balance:,.0f} KRW\n"
        message += f"KRW 잔고: {krw_balance:,.0f} KRW\n"
        message += f"위험 수준: {risk_level}\n\n"
        
        # 코인별 상세 정보
        exposure = portfolio_info.get('portfolio_exposure', {})
        
        if exposure:
            message += "<b>보유 코인:</b>\n"
            
            for ticker, info in exposure.items():
                message += f"- {ticker}: {info.get('quantity', 0):.8f} "
                message += f"({info.get('value', 0):,.0f} KRW, {info.get('ratio', 0):.2%})\n"
        
        return self.send_message(message)
    
    def notify_error(self, module, error_msg):
        """
        오류 알림 전송
        
        Args:
            module (str): 오류 발생 모듈
            error_msg (str): 오류 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 메시지 생성
        message = f"<b>[오류 발생]</b> ({timestamp})\n\n"
        message += f"모듈: {module}\n"
        message += f"내용: {error_msg}\n"
        
        return self.send_message(message)
    
    def notify_startup(self, version="1.0.0"):
        """
        시작 알림 전송
        
        Args:
            version (str): 봇 버전
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            return False
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 메시지 생성
        message = f"<b>[업비트 트레이딩 봇 시작]</b> ({timestamp})\n\n"
        message += f"버전: {version}\n"
        message += "텔레그램 알림이 정상적으로 설정되었습니다.\n"
        
        return self.send_message(message)
